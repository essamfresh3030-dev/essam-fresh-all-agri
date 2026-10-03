from datetime import datetime, timedelta
from decimal import Decimal
import os, json, hashlib, hmac
import jwt
from fastapi import APIRouter, Depends, HTTPException, Header, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import func, inspect, text
from .db import Base, engine, get_db
from . import models, schemas
router=APIRouter()
JWT_SECRET=os.getenv("JWT_SECRET","change-this-secret-in-production")
JWT_ALG="HS256"

def hash_password(password:str)->str:
    salt=os.urandom(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,120000)
    return salt.hex()+":"+digest.hex()

def verify_password(password:str, stored:str)->bool:
    try:
        salt_hex,digest_hex=stored.split(":",1)
        digest=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt_hex),120000)
        return hmac.compare_digest(digest.hex(),digest_hex)
    except Exception:
        return False

def create_token(user):
    return jwt.encode({"sub":user.id,"username":user.username,"exp":datetime.utcnow()+timedelta(hours=12)},JWT_SECRET,algorithm=JWT_ALG)

def current_user(authorization:str|None=Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401,"Bearer token required")
    try:
        payload=jwt.decode(authorization.split(" ",1)[1],JWT_SECRET,algorithms=[JWT_ALG])
        uid=payload.get("sub")
        if not uid: raise ValueError()
        return uid
    except Exception:
        raise HTTPException(401,"invalid or expired token")

def has_permission(db,user_id,code):
    u=db.get(models.User,user_id)
    if not u or not u.active: return False
    roles=db.query(models.UserRole).filter_by(user_id=user_id).all()
    if any((r.role_id==db.query(models.Role).filter_by(name="ADMIN").first().id) for r in roles if db.query(models.Role).filter_by(name="ADMIN").first()): return True
    p=db.query(models.Permission).filter_by(code=code).first()
    if not p: return False
    return db.query(models.RolePermission).filter(models.RolePermission.permission_id==p.id, models.RolePermission.role_id.in_([r.role_id for r in roles])).first() is not None

def require_permission(db,user_id,code):
    if not has_permission(db,user_id,code): raise HTTPException(403,f"permission required: {code}")

def audit(db,user_id,action,entity_type,entity_id=None,metadata=None):
    db.add(models.AuditLog(user_id=user_id,action=action,entity_type=entity_type,entity_id=entity_id,metadata_json=json.dumps(metadata or {},ensure_ascii=False)))

def dec(x): return Decimal(str(x))
def crud_create(db, model, data):
    obj=model(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

def post_journal(db, x):
    debit=sum(dec(l.debit) for l in x.lines); credit=sum(dec(l.credit) for l in x.lines)
    if debit<=0 or debit!=credit: raise HTTPException(400,"Journal must be balanced and contain a positive debit total")
    e=models.JournalEntry(company_id=x.company_id,entry_no=x.entry_no,entry_date=x.entry_date,description=x.description,source_type=x.source_type,source_id=x.source_id,posted=True)
    db.add(e); db.flush()
    for l in x.lines:
        if dec(l.debit)<0 or dec(l.credit)<0 or (dec(l.debit)>0 and dec(l.credit)>0): raise HTTPException(400,"Each journal line must be debit or credit")
        db.add(models.JournalLine(journal_entry_id=e.id,**l.model_dump()))
    db.commit(); db.refresh(e); return e

@router.post("/system/init")
def init_db(db:Session=Depends(get_db)):
    Base.metadata.create_all(bind=engine)
    # Lightweight migration for installations created by v0.8 and earlier.
    insp=inspect(engine)
    cols={c["name"] for c in insp.get_columns("purchase_invoices")} if insp.has_table("purchase_invoices") else set()
    additions={"subtotal":"NUMERIC(18,2) DEFAULT 0","vat_rate":"NUMERIC(8,4) DEFAULT 0","vat_amount":"NUMERIC(18,2) DEFAULT 0","grand_total":"NUMERIC(18,2) DEFAULT 0","vat_account_id":"VARCHAR(36)","receipt_id":"VARCHAR(36)","approved_by":"VARCHAR(36)","approved_at":"TIMESTAMP"}
    for table in ("purchase_quotations","purchase_orders"):
        if insp.has_table(table):
            qcols={c["name"] for c in insp.get_columns(table)}
            if "vat_enabled" not in qcols:
                db.execute(text(f"ALTER TABLE {table} ADD COLUMN vat_enabled BOOLEAN DEFAULT FALSE"))
    if "vat_enabled" not in cols: additions["vat_enabled"]="BOOLEAN DEFAULT FALSE"
    for name,typ in additions.items():
        if name not in cols:
            db.execute(text(f"ALTER TABLE purchase_invoices ADD COLUMN {name} {typ}"))
    for table in ("purchase_quotations","purchase_orders","goods_receipts","inventory_issues"):
        if insp.has_table(table):
            tcols={c["name"] for c in insp.get_columns(table)}
            for name,typ in (("approved_by","VARCHAR(36)"),("approved_at","TIMESTAMP")):
                if name not in tcols: db.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {typ}"))
    # v1.3 inventory master fields
    if insp.has_table("items"):
        item_cols={c["name"] for c in insp.get_columns("items")}
        for name,typ in (("min_stock","NUMERIC(18,4) DEFAULT 0"),("reorder_level","NUMERIC(18,4) DEFAULT 0"),("standard_cost","NUMERIC(18,4) DEFAULT 0")):
            if name not in item_cols: db.execute(text(f"ALTER TABLE items ADD COLUMN {name} {typ}"))
    db.commit()
    roles=("ADMIN","Full system administration"),("ACCOUNTANT","Accounting and finance"),("FARM_MANAGER","Farm operations"),("FIELD_USER","Field data entry"),("SALES","Sales and export")
    for name,desc in roles:
        if not db.query(models.Role).filter_by(name=name).first(): db.add(models.Role(name=name,description=desc))
    perms=["system.admin","farm.read","farm.write","inventory.read","inventory.write","accounting.read","accounting.write","sales.read","sales.write","sync.write"]
    for code in perms:
        if not db.query(models.Permission).filter_by(code=code).first(): db.add(models.Permission(code=code))
    db.commit()
    admin=db.query(models.User).filter_by(username="admin").first()
    if not admin:
        admin=models.User(username="admin",full_name="System Administrator",password_hash=hash_password(os.getenv("ADMIN_PASSWORD","ChangeMe123!")),active=True)
        db.add(admin); db.commit(); db.refresh(admin)
    admin_role=db.query(models.Role).filter_by(name="ADMIN").first()
    if admin_role and not db.query(models.UserRole).filter_by(user_id=admin.id,role_id=admin_role.id).first():
        db.add(models.UserRole(user_id=admin.id,role_id=admin_role.id)); db.commit()
    if admin_role:
        for perm in db.query(models.Permission).all():
            if not db.query(models.RolePermission).filter_by(role_id=admin_role.id,permission_id=perm.id).first(): db.add(models.RolePermission(role_id=admin_role.id,permission_id=perm.id))
        db.commit()
    return {"status":"initialized","default_admin":"admin","password_source":"ADMIN_PASSWORD env or ChangeMe123!"}
@router.get("/health")
def health(): return {"status":"ok","version":"2.1.0"}

@router.get("/sectors")
def sectors(db:Session=Depends(get_db)): return db.query(models.Sector).all()
@router.get("/farms")
def farms(db:Session=Depends(get_db)): return db.query(models.Farm).all()
@router.get("/clusters")
def clusters(db:Session=Depends(get_db)): return db.query(models.Cluster).all()
@router.get("/greenhouses")
def greenhouses(db:Session=Depends(get_db)): return db.query(models.Greenhouse).all()
@router.get("/crop-cycles")
def crop_cycles(db:Session=Depends(get_db)): return db.query(models.CropCycle).all()
@router.get("/companies")
def companies(db:Session=Depends(get_db)): return db.query(models.Company).all()
@router.get("/items")
def items(db:Session=Depends(get_db)): return db.query(models.Item).all()
@router.get("/suppliers")
def suppliers(db:Session=Depends(get_db)): return db.query(models.Supplier).all()
@router.get("/warehouses")
def warehouses(db:Session=Depends(get_db)): return db.query(models.Warehouse).all()
@router.get("/accounts")
def accounts(db:Session=Depends(get_db)): return db.query(models.Account).all()

@router.post("/companies")
def company(x:schemas.CompanyCreate,db:Session=Depends(get_db)): return crud_create(db,models.Company,x)
@router.post("/sectors")
def sector(x:schemas.SectorCreate,db:Session=Depends(get_db)): return crud_create(db,models.Sector,x)
@router.post("/farms")
def farm(x:schemas.FarmCreate,db:Session=Depends(get_db)): return crud_create(db,models.Farm,x)
@router.post("/clusters")
def cluster(x:schemas.ClusterCreate,db:Session=Depends(get_db)): return crud_create(db,models.Cluster,x)
@router.post("/greenhouses")
def greenhouse(x:schemas.GreenhouseCreate,db:Session=Depends(get_db)): return crud_create(db,models.Greenhouse,x)
@router.post("/crops")
def crop(x:schemas.CropCreate,db:Session=Depends(get_db)): return crud_create(db,models.Crop,x)
@router.post("/crop-cycles")
def cycle(x:schemas.CropCycleCreate,db:Session=Depends(get_db)): return crud_create(db,models.CropCycle,x)
@router.post("/cost-centers")
def cost_center(x:schemas.CostCenterCreate,db:Session=Depends(get_db)): return crud_create(db,models.CostCenter,x)
@router.post("/accounts")
def account(x:schemas.AccountCreate,db:Session=Depends(get_db)): return crud_create(db,models.Account,x)
@router.post("/journals")
def journal(x:schemas.JournalCreate,db:Session=Depends(get_db)): return post_journal(db,x)
@router.post("/items")
def item(x:schemas.ItemCreate,db:Session=Depends(get_db)): return crud_create(db,models.Item,x)
@router.post("/warehouses")
def warehouse(x:schemas.WarehouseCreate,db:Session=Depends(get_db)): return crud_create(db,models.Warehouse,x)

@router.post("/inventory/transactions")
def inventory(x:schemas.InventoryCreate,db:Session=Depends(get_db)):
    if x.quantity<=0: raise HTTPException(400,"quantity must be positive")
    if x.transaction_type not in ("IN","OUT","ADJUSTMENT"): raise HTTPException(400,"invalid transaction_type")
    item=db.get(models.Item,x.item_id)
    if not item: raise HTTPException(404,"item not found")
    total=dec(x.quantity)*dec(x.unit_cost)
    if x.transaction_type=="OUT":
        q=db.query(func.coalesce(func.sum(models.InventoryTransaction.quantity),0)).filter(models.InventoryTransaction.item_id==x.item_id,models.InventoryTransaction.warehouse_id==x.warehouse_id).scalar()
        # MVP stock balance: IN positive, OUT negative, adjustment interpreted by supplied quantity.
        balance=dec(q or 0)
        if balance<dec(x.quantity): raise HTTPException(400,f"insufficient stock: available={balance}")
    obj=models.InventoryTransaction(item_id=x.item_id,warehouse_id=x.warehouse_id,crop_cycle_id=x.crop_cycle_id,transaction_type=x.transaction_type,quantity=(x.quantity if x.transaction_type!="OUT" else -x.quantity),unit_cost=x.unit_cost,total_cost=total,batch_no=x.batch_no,expiry_date=x.expiry_date,transaction_date=datetime.utcnow())
    db.add(obj); db.flush()
    if x.crop_cycle_id and x.transaction_type=="OUT":
        db.add(models.CropCost(crop_cycle_id=x.crop_cycle_id,cost_type="MATERIAL",description="صرف مخزني",amount=total,source_type="INVENTORY",source_id=obj.id,cost_date=datetime.utcnow().date(),cost_center_id=x.cost_center_id))
    # Accounting: Inventory IN => Dr Inventory / Cr Clearing; OUT => Dr Crop Cost/Expense / Cr Inventory.
    if item.inventory_account_id:
        if x.transaction_type=="IN":
            lines=[schemas.JournalLineCreate(account_id=item.inventory_account_id,debit=float(total)), schemas.JournalLineCreate(account_id=item.expense_account_id or item.inventory_account_id,credit=float(total))]
        elif x.transaction_type=="OUT":
            lines=[schemas.JournalLineCreate(account_id=item.expense_account_id or item.inventory_account_id,debit=float(total),cost_center_id=x.cost_center_id), schemas.JournalLineCreate(account_id=item.inventory_account_id,credit=float(total))]
        else: lines=[]
        if lines:
            # determine company through crop cycle hierarchy where possible; otherwise first company.
            company_id=None
            if x.crop_cycle_id:
                cc=db.get(models.CropCycle,x.crop_cycle_id); gh=db.get(models.Greenhouse,cc.greenhouse_id) if cc else None; cl=db.get(models.Cluster,gh.cluster_id) if gh else None; f=db.get(models.Farm,cl.farm_id) if cl else None; s=db.get(models.Sector,f.sector_id) if f else None; company_id=s.company_id if s else None
            company_id=company_id or db.query(models.Company.id).first()[0] if db.query(models.Company.id).first() else None
            if company_id:
                j=schemas.JournalCreate(company_id=company_id,entry_no=f"INV-{obj.id[:8]}",entry_date=datetime.utcnow().date(),description="Inventory transaction",source_type="INVENTORY",source_id=obj.id,lines=lines)
                e=post_journal(db,j); obj.journal_entry_id=e.id
    db.commit(); db.refresh(obj); return obj

@router.get("/farm-operations")
def farm_operations(crop_cycle_id:str|None=None, db:Session=Depends(get_db)):
    q=db.query(models.FarmOperation)
    if crop_cycle_id: q=q.filter(models.FarmOperation.crop_cycle_id==crop_cycle_id)
    return q.order_by(models.FarmOperation.operation_date.desc()).all()


@router.get("/farm-operations/{operation_id}")
def farm_operation(operation_id:str,db:Session=Depends(get_db)):
    obj=db.get(models.FarmOperation,operation_id)
    if not obj: raise HTTPException(404,"farm operation not found")
    return obj

@router.get("/inventory/balance/{item_id}/{warehouse_id}")
def inventory_balance(item_id:str,warehouse_id:str,db:Session=Depends(get_db)):
    item=db.get(models.Item,item_id)
    if not item: raise HTTPException(404,"item not found")
    q=db.query(func.coalesce(func.sum(models.InventoryTransaction.quantity),0)).filter(models.InventoryTransaction.item_id==item_id,models.InventoryTransaction.warehouse_id==warehouse_id).scalar()
    return {"item_id":item_id,"warehouse_id":warehouse_id,"balance":float(q or 0),"unit":item.unit}

@router.get("/crop-costs/{crop_cycle_id}")
def crop_costs(crop_cycle_id:str, db:Session=Depends(get_db)):
    rows=db.query(models.CropCost).filter(models.CropCost.crop_cycle_id==crop_cycle_id).all()
    total=sum(dec(r.amount) for r in rows)
    return {"crop_cycle_id":crop_cycle_id,"total_cost":float(total),"by_type":{t:float(sum(dec(r.amount) for r in rows if r.cost_type==t)) for t in sorted(set(r.cost_type for r in rows))},"rows":rows}

@router.post("/farm-operations")
def farm_operation(x:schemas.FarmOperationCreate, db:Session=Depends(get_db)):
    if x.operation_type not in ("IRRIGATION","FERTILIZATION","PESTICIDE","LABOR","HARVEST","WASTE","OTHER"):
        raise HTTPException(400,"invalid operation_type")
    cc=db.get(models.CropCycle,x.crop_cycle_id)
    if not cc: raise HTTPException(404,"crop cycle not found")
    if x.amount < 0: raise HTTPException(400,"amount cannot be negative")
    obj=models.FarmOperation(**x.model_dump())
    db.add(obj); db.flush()
    if x.amount>0:
        cost_type={"IRRIGATION":"IRRIGATION","FERTILIZATION":"FERTILIZER","PESTICIDE":"PESTICIDE","LABOR":"LABOR","HARVEST":"HARVEST","WASTE":"WASTE"}.get(x.operation_type,"OTHER")
        db.add(models.CropCost(crop_cycle_id=x.crop_cycle_id,cost_type=cost_type,description=x.description or x.operation_type,amount=x.amount,source_type="FARM_OPERATION",source_id=obj.id,cost_date=x.operation_date,cost_center_id=x.cost_center_id))
    db.commit(); db.refresh(obj); return obj

@router.post("/suppliers")
def supplier(x:schemas.SupplierCreate,db:Session=Depends(get_db)): return crud_create(db,models.Supplier,x)
@router.get("/purchase-quotations")
def purchase_quotations(db:Session=Depends(get_db)): return db.query(models.PurchaseQuotation).order_by(models.PurchaseQuotation.quotation_date.desc()).all()

@router.get("/purchase-orders")
def purchase_orders(db:Session=Depends(get_db)): return db.query(models.PurchaseOrder).order_by(models.PurchaseOrder.order_date.desc()).all()
@router.get("/purchase-orders/{order_id}/lines")
def purchase_order_lines(order_id:str,db:Session=Depends(get_db)):
    if not db.get(models.PurchaseOrder,order_id): raise HTTPException(404,"purchase order not found")
    return db.query(models.PurchaseOrderLine).filter_by(purchase_order_id=order_id).all()

@router.get("/goods-receipts")
def goods_receipts(db:Session=Depends(get_db)): return db.query(models.GoodsReceipt).order_by(models.GoodsReceipt.receipt_date.desc()).all()

@router.get("/inventory/issues")
def inventory_issues(db:Session=Depends(get_db)): return db.query(models.InventoryIssue).order_by(models.InventoryIssue.issue_date.desc()).all()

@router.get("/vat-settings/summary")
def vat_settings_summary():
    return {"options":[{"code":"WITH_VAT","label":"خاضع لضريبة القيمة المضافة"},{"code":"WITHOUT_VAT","label":"بدون ضريبة القيمة المضافة"}],"default_rate":14}

@router.post("/purchase-quotations")
def purchase_quotation(x:schemas.PurchaseQuotationCreate,db:Session=Depends(get_db)):
    if not 0 <= x.vat_rate <= 100: raise HTTPException(400,"vat_rate must be between 0 and 100")
    subtotal=Decimal("0"); rows=[]
    for l in x.lines:
        q=dec(l["quantity"]); price=dec(l["unit_price"])
        if q<=0 or price<0: raise HTTPException(400,"invalid quotation line")
        total=q*price; subtotal+=total; rows.append((l,total))
    vat=(subtotal*dec(x.vat_rate)/Decimal("100")) if x.vat_enabled else Decimal("0"); grand=subtotal+vat
    vat_rate=x.vat_rate if x.vat_enabled else 0
    obj=models.PurchaseQuotation(supplier_id=x.supplier_id,company_id=x.company_id,quotation_no=x.quotation_no,quotation_date=x.quotation_date,valid_until=x.valid_until,currency=x.currency,exchange_rate=x.exchange_rate,vat_enabled=x.vat_enabled,subtotal=subtotal,vat_rate=vat_rate,vat_amount=vat,grand_total=grand)
    db.add(obj); db.flush()
    for l,total in rows: db.add(models.PurchaseQuotationLine(quotation_id=obj.id,item_id=l["item_id"],quantity=l["quantity"],unit_price=l["unit_price"],total=total))
    db.commit(); db.refresh(obj); return obj

@router.post("/purchase-orders")
def purchase_order(x:schemas.PurchaseOrderCreate,db:Session=Depends(get_db)):
    sup=db.get(models.Supplier,x.supplier_id)
    if not sup: raise HTTPException(404,"supplier not found")
    if x.quotation_id and not db.get(models.PurchaseQuotation,x.quotation_id): raise HTTPException(404,"quotation not found")
    if not 0 <= x.vat_rate <= 100: raise HTTPException(400,"vat_rate must be between 0 and 100")
    subtotal=Decimal("0"); rows=[]
    for l in x.lines:
        q=dec(l["quantity"]); price=dec(l["unit_price"])
        if q<=0 or price<0: raise HTTPException(400,"invalid purchase order line")
        if not db.get(models.Item,l["item_id"]): raise HTTPException(404,"item not found")
        if not db.get(models.Warehouse,l["warehouse_id"]): raise HTTPException(404,"warehouse not found")
        total=q*price; subtotal+=total; rows.append((l,total))
    vat=(subtotal*dec(x.vat_rate)/Decimal("100")) if x.vat_enabled else Decimal("0"); grand=subtotal+vat
    vat_rate=x.vat_rate if x.vat_enabled else 0
    obj=models.PurchaseOrder(supplier_id=x.supplier_id,company_id=x.company_id,order_no=x.order_no,order_date=x.order_date,quotation_id=x.quotation_id,currency=x.currency,exchange_rate=x.exchange_rate,vat_enabled=x.vat_enabled,subtotal=subtotal,vat_rate=vat_rate,vat_amount=vat,grand_total=grand)
    db.add(obj); db.flush()
    for l,total in rows: db.add(models.PurchaseOrderLine(purchase_order_id=obj.id,item_id=l["item_id"],warehouse_id=l["warehouse_id"],quantity=l["quantity"],unit_price=l["unit_price"],total=total))
    db.commit(); db.refresh(obj); return obj

@router.post("/goods-receipts")
def goods_receipt(x:schemas.GoodsReceiptCreate,db:Session=Depends(get_db)):
    po=db.get(models.PurchaseOrder,x.purchase_order_id)
    if not po: raise HTTPException(404,"purchase order not found")
    obj=models.GoodsReceipt(purchase_order_id=po.id,receipt_no=x.receipt_no,receipt_date=x.receipt_date)
    db.add(obj); db.flush()
    for l in x.lines:
        q=dec(l["quantity"]); cost=dec(l.get("unit_cost",0))
        if q<=0 or cost<0: raise HTTPException(400,"invalid receipt line")
        pol=db.get(models.PurchaseOrderLine,l["purchase_order_line_id"])
        if not pol or pol.purchase_order_id!=po.id: raise HTTPException(400,"invalid purchase_order_line_id")
        if q>dec(pol.quantity): raise HTTPException(400,"received quantity exceeds ordered quantity")
        grl=models.GoodsReceiptLine(receipt_id=obj.id,item_id=pol.item_id,warehouse_id=pol.warehouse_id,quantity=q,unit_cost=(cost if cost>0 else dec(pol.unit_price)),batch_no=l.get("batch_no"),expiry_date=l.get("expiry_date")); db.add(grl); db.flush()
        db.add(models.InventoryTransaction(item_id=pol.item_id,warehouse_id=pol.warehouse_id,transaction_type="IN",quantity=q,unit_cost=grl.unit_cost,total_cost=q*grl.unit_cost,batch_no=grl.batch_no,expiry_date=grl.expiry_date,transaction_date=datetime.utcnow()))
    db.commit(); db.refresh(obj); return obj

@router.post("/purchase-invoices")
def purchase(x:schemas.PurchaseInvoiceCreate,db:Session=Depends(get_db)):
    sup=db.get(models.Supplier,x.supplier_id)
    if not sup: raise HTTPException(404,"supplier not found")
    if not 0 <= x.vat_rate <= 100: raise HTTPException(400,"vat_rate must be between 0 and 100")
    if x.receipt_id and not db.get(models.GoodsReceipt,x.receipt_id): raise HTTPException(404,"goods receipt not found")
    subtotal=Decimal("0"); lines=[]
    for l in x.lines:
        q=dec(l["quantity"]); c=dec(l["unit_cost"])
        if q<=0 or c<0: raise HTTPException(400,"invalid purchase line")
        t=q*c; subtotal+=t; lines.append((l,q,c,t))
    vat=(subtotal*dec(x.vat_rate)/Decimal("100")) if x.vat_enabled else Decimal("0"); grand=subtotal+vat
    vat_rate=x.vat_rate if x.vat_enabled else 0
    if vat>0 and not x.vat_account_id: raise HTTPException(400,"vat_account_id is required when VAT is greater than zero")
    inv=models.PurchaseInvoice(supplier_id=x.supplier_id,company_id=x.company_id,invoice_no=x.invoice_no,invoice_date=x.invoice_date,currency=x.currency,exchange_rate=x.exchange_rate,total=grand,vat_enabled=x.vat_enabled,subtotal=subtotal,vat_rate=vat_rate,vat_amount=vat,grand_total=grand,vat_account_id=x.vat_account_id,receipt_id=x.receipt_id,status="DRAFT")
    db.add(inv); db.flush()
    for l,q,c,t in lines:
        db.add(models.PurchaseLine(purchase_invoice_id=inv.id,item_id=l["item_id"],warehouse_id=l["warehouse_id"],quantity=q,unit_cost=c,total=t))
        if not x.receipt_id:
            db.add(models.InventoryTransaction(item_id=l["item_id"],warehouse_id=l["warehouse_id"],transaction_type="IN",quantity=q,unit_cost=c,total_cost=t,transaction_date=datetime.utcnow()))
    db.commit(); db.refresh(inv); return inv


@router.get("/purchase-invoices")
def purchase_invoices(db:Session=Depends(get_db)):
    return db.query(models.PurchaseInvoice).order_by(models.PurchaseInvoice.invoice_date.desc()).all()

@router.post("/purchase-invoices/{invoice_id}/approve")
def approve_purchase_invoice(invoice_id:str, db:Session=Depends(get_db), user_id:str=Depends(current_user)):
    require_permission(db,user_id,"accounting.write")
    inv=db.get(models.PurchaseInvoice,invoice_id)
    if not inv: raise HTTPException(404,"purchase invoice not found")
    if inv.status=="APPROVED": return inv
    if inv.status!="DRAFT": raise HTTPException(400,f"invoice status {inv.status} cannot be approved")
    sup=db.get(models.Supplier,inv.supplier_id)
    if not sup or not sup.payable_account_id: raise HTTPException(400,"supplier payable_account_id is required")
    lines=db.query(models.PurchaseLine).filter_by(purchase_invoice_id=inv.id).all()
    inv_accounts=[]
    for l in lines:
        item=db.get(models.Item,l.item_id)
        if not item or not item.inventory_account_id: raise HTTPException(400,"each purchased item needs inventory_account_id")
        t=dec(l.total); inv_accounts.append(schemas.JournalLineCreate(account_id=item.inventory_account_id,debit=float(t*dec(inv.exchange_rate))))
        if not inv.receipt_id:
            db.add(models.InventoryTransaction(item_id=l.item_id,warehouse_id=l.warehouse_id,transaction_type="IN",quantity=l.quantity,unit_cost=l.unit_cost,total_cost=l.total,transaction_date=datetime.utcnow()))
    if dec(inv.vat_amount)>0:
        if not inv.vat_account_id: raise HTTPException(400,"vat_account_id is required when VAT is greater than zero")
        inv_accounts.append(schemas.JournalLineCreate(account_id=inv.vat_account_id,debit=float(dec(inv.vat_amount)*dec(inv.exchange_rate))))
    inv_accounts.append(schemas.JournalLineCreate(account_id=sup.payable_account_id,credit=float(dec(inv.grand_total)*dec(inv.exchange_rate))))
    j=schemas.JournalCreate(company_id=inv.company_id,entry_no=f"PUR-{inv.invoice_no}",entry_date=inv.invoice_date,description=f"Purchase invoice {inv.invoice_no}",source_type="PURCHASE",source_id=inv.id,lines=inv_accounts)
    e=post_journal(db,j)
    inv.journal_entry_id=e.id; inv.status="APPROVED"; inv.approved_by=user_id; inv.approved_at=datetime.utcnow()
    audit(db,user_id,"APPROVE","PurchaseInvoice",inv.id,{"invoice_no":inv.invoice_no,"grand_total":float(inv.grand_total)})
    db.commit(); db.refresh(inv); return inv

@router.post("/purchase-invoices/{invoice_id}/pdf")
def purchase_invoice_pdf(invoice_id:str, db:Session=Depends(get_db), user_id:str=Depends(current_user)):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from io import BytesIO
    inv=db.get(models.PurchaseInvoice,invoice_id)
    if not inv: raise HTTPException(404,"purchase invoice not found")
    buf=BytesIO(); c=canvas.Canvas(buf,pagesize=(595,842))
    font="Helvetica"
    try:
        pdfmetrics.registerFont(TTFont("DejaVu","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")); font="DejaVu"
    except Exception: pass
    c.setFont(font,16); c.drawString(40,800,"Agri ERP - Purchase Invoice")
    c.setFont(font,10)
    rows=[("Invoice No",inv.invoice_no),("Date",str(inv.invoice_date)),("Status",inv.status),("Subtotal",f"{inv.subtotal}"),("VAT Enabled",str(bool(inv.vat_enabled))), ("VAT Rate",f"{inv.vat_rate}%"),("VAT Amount",f"{inv.vat_amount}"),("Grand Total",f"{inv.grand_total}"),("Currency",inv.currency)]
    y=770
    for k,v in rows: c.drawString(45,y,f"{k}: {v}"); y-=24
    c.drawString(45,y,"Items"); y-=20
    for l in db.query(models.PurchaseLine).filter_by(purchase_invoice_id=inv.id).all():
        c.drawString(55,y,f"{l.item_id} | Qty {l.quantity} | Unit {l.unit_cost} | Total {l.total}"); y-=20
        if y<60: c.showPage(); c.setFont(font,10); y=800
    c.save(); data=buf.getvalue(); return Response(content=data,media_type="application/pdf",headers={"Content-Disposition":f'inline; filename="purchase_invoice_{inv.invoice_no}.pdf"'})

@router.post("/purchase-orders/{order_id}/approve")
def approve_purchase_order(order_id:str, db:Session=Depends(get_db), user_id:str=Depends(current_user)):
    require_permission(db,user_id,"inventory.write")
    obj=db.get(models.PurchaseOrder,order_id)
    if not obj: raise HTTPException(404,"purchase order not found")
    if obj.status=="APPROVED": return obj
    if obj.status!="DRAFT": raise HTTPException(400,"purchase order is not draft")
    obj.status="APPROVED"; obj.approved_by=user_id; obj.approved_at=datetime.utcnow(); audit(db,user_id,"APPROVE","PurchaseOrder",obj.id,{"order_no":obj.order_no}); db.commit(); db.refresh(obj); return obj

@router.post("/purchase-quotations/{quotation_id}/approve")
def approve_purchase_quotation(quotation_id:str, db:Session=Depends(get_db), user_id:str=Depends(current_user)):
    require_permission(db,user_id,"inventory.write")
    obj=db.get(models.PurchaseQuotation,quotation_id)
    if not obj: raise HTTPException(404,"quotation not found")
    if obj.status=="APPROVED": return obj
    if obj.status!="DRAFT": raise HTTPException(400,"quotation is not draft")
    obj.status="APPROVED"; obj.approved_by=user_id; obj.approved_at=datetime.utcnow(); audit(db,user_id,"APPROVE","PurchaseQuotation",obj.id,{"quotation_no":obj.quotation_no}); db.commit(); db.refresh(obj); return obj

@router.post("/inventory/issues")
def inventory_issue(x:schemas.InventoryIssueCreate,db:Session=Depends(get_db)):
    if not db.get(models.Warehouse,x.warehouse_id): raise HTTPException(404,"warehouse not found")
    obj=models.InventoryIssue(issue_no=x.issue_no,issue_date=x.issue_date,warehouse_id=x.warehouse_id,crop_cycle_id=x.crop_cycle_id,cost_center_id=x.cost_center_id)
    db.add(obj); db.flush()
    total=Decimal("0")
    for l in x.lines:
        item=db.get(models.Item,l["item_id"])
        if not item: raise HTTPException(404,"item not found")
        q=dec(l["quantity"])
        if q<=0: raise HTTPException(400,"quantity must be positive")
        balance=dec(db.query(func.coalesce(func.sum(models.InventoryTransaction.quantity),0)).filter(models.InventoryTransaction.item_id==l["item_id"],models.InventoryTransaction.warehouse_id==x.warehouse_id).scalar() or 0)
        if balance<q: raise HTTPException(400,f"insufficient stock for {l['item_id']}: available={balance}")
        net_in=db.query(func.coalesce(func.sum(models.InventoryTransaction.total_cost),0)).filter(models.InventoryTransaction.item_id==l["item_id"],models.InventoryTransaction.warehouse_id==x.warehouse_id,models.InventoryTransaction.transaction_type=="IN").scalar() or 0
        net_out=db.query(func.coalesce(func.sum(models.InventoryTransaction.total_cost),0)).filter(models.InventoryTransaction.item_id==l["item_id"],models.InventoryTransaction.warehouse_id==x.warehouse_id,models.InventoryTransaction.transaction_type=="OUT").scalar() or 0
        unit=dec(l.get("unit_cost",0)) or ((dec(net_in)-dec(net_out))/balance if balance else Decimal("0"))
        cost=q*unit; total+=cost
        db.add(models.InventoryIssueLine(issue_id=obj.id,item_id=item.id,quantity=q,unit_cost=unit,total_cost=cost))
        db.add(models.InventoryTransaction(item_id=item.id,warehouse_id=x.warehouse_id,crop_cycle_id=x.crop_cycle_id,transaction_type="OUT",quantity=-q,unit_cost=unit,total_cost=cost,transaction_date=datetime.utcnow()))
        if x.crop_cycle_id: db.add(models.CropCost(crop_cycle_id=x.crop_cycle_id,cost_type="MATERIAL",description=f"إذن صرف {x.issue_no}",amount=cost,source_type="INVENTORY_ISSUE",source_id=obj.id,cost_date=x.issue_date,cost_center_id=x.cost_center_id))
    db.commit(); db.refresh(obj); return {"id":obj.id,"issue_no":obj.issue_no,"total_cost":float(total),"status":obj.status}

@router.post("/customers")
def customer(x:schemas.CustomerCreate,db:Session=Depends(get_db)): return crud_create(db,models.Customer,x)
@router.post("/sales/orders")
def sales_order(x:schemas.SalesOrderCreate,db:Session=Depends(get_db)):
    if x.channel not in ("LOCAL","EXPORT"): raise HTTPException(400,"channel must be LOCAL or EXPORT")
    if x.channel=="EXPORT" and not x.destination_country: raise HTTPException(400,"destination_country is required for export")
    if x.exchange_rate<=0: raise HTTPException(400,"exchange_rate must be positive")
    return crud_create(db,models.SalesOrder,x)
@router.post("/sales/lines")
def sales_line(x:schemas.SalesLineCreate,db:Session=Depends(get_db)):
    if x.quantity<=0 or x.unit_price<0: raise HTTPException(400,"invalid quantity/price")
    data=x.model_dump(); data["total"]=x.quantity*x.unit_price
    obj=models.SalesLine(**data); db.add(obj); db.commit(); db.refresh(obj); return obj
@router.post("/sales/quotations")
def sales_quotation(x:schemas.SalesQuotationCreate, db:Session=Depends(get_db)):
    if x.channel not in ("LOCAL","EXPORT"): raise HTTPException(400,"channel must be LOCAL or EXPORT")
    if x.exchange_rate<=0 or x.vat_rate<0: raise HTTPException(400,"invalid exchange_rate/vat_rate")
    if x.channel=="LOCAL" and x.vat_enabled: raise HTTPException(400,"LOCAL sales must be without VAT")
    if x.channel=="LOCAL" and x.vat_rate!=0: raise HTTPException(400,"LOCAL sales VAT rate must be zero")
    subtotal=0; rows=[]
    for l in x.lines:
        q=dec(l.get("quantity",0)); price=dec(l.get("unit_price",0))
        if q<=0 or price<0: raise HTTPException(400,"invalid sales quotation line")
        total=q*price; subtotal+=total; rows.append((l,total))
    vat=(subtotal*dec(x.vat_rate)/100) if x.vat_enabled else dec(0); grand=subtotal+vat
    obj=models.SalesQuotation(customer_id=x.customer_id,company_id=x.company_id,quotation_no=x.quotation_no,quotation_date=x.quotation_date,valid_until=x.valid_until,channel=x.channel,currency=x.currency,exchange_rate=x.exchange_rate,vat_enabled=x.vat_enabled,vat_rate=x.vat_rate,subtotal=subtotal,vat_amount=vat,grand_total=grand)
    db.add(obj); db.flush()
    for l,total in rows: db.add(models.SalesQuotationLine(quotation_id=obj.id,description=l.get("description", ""),crop_cycle_id=l.get("crop_cycle_id"),quantity=l["quantity"],unit_price=l["unit_price"],total=total))
    db.commit(); db.refresh(obj); return obj

@router.post("/sales/invoices")
def sales_invoice(x:schemas.SalesInvoiceCreate,db:Session=Depends(get_db)):
    order=db.get(models.SalesOrder,x.sales_order_id)
    if not order: raise HTTPException(404,"sales order not found")
    lines=db.query(models.SalesLine).filter_by(sales_order_id=order.id).all()
    if not lines: raise HTTPException(400,"sales order has no lines")
    if x.vat_rate<0: raise HTTPException(400,"vat_rate must be non-negative")
    if order.channel=="LOCAL" and x.vat_enabled: raise HTTPException(400,"LOCAL sales invoices must be without VAT")
    if order.channel=="LOCAL" and x.vat_rate!=0: raise HTTPException(400,"LOCAL sales VAT rate must be zero")
    subtotal=sum(dec(l.total) for l in lines)
    vat=(subtotal*dec(x.vat_rate)/100) if x.vat_enabled else dec(0)
    total=subtotal+vat; total_egp=total*dec(order.exchange_rate)
    inv=models.SalesInvoice(sales_order_id=order.id,invoice_no=x.invoice_no,invoice_date=x.invoice_date,total=total,subtotal=subtotal,vat_enabled=x.vat_enabled,vat_rate=x.vat_rate,vat_amount=vat,total_egp=total_egp)
    db.add(inv); db.flush()
    customer=db.get(models.Customer,order.customer_id)
    if not customer or not customer.receivable_account_id: raise HTTPException(400,"customer receivable_account_id is required")
    company_id=db.query(models.Company.id).first()[0] if db.query(models.Company.id).first() else None
    revenue_account=db.query(models.Account).filter(models.Account.company_id==company_id,models.Account.account_type=="REVENUE",models.Account.is_postable==True).first() if company_id else None
    if not revenue_account: raise HTTPException(400,"configure a postable REVENUE account first")
    jlines=[schemas.JournalLineCreate(account_id=customer.receivable_account_id,debit=float(total_egp)),schemas.JournalLineCreate(account_id=revenue_account.id,credit=float(subtotal*dec(order.exchange_rate)))]
    if x.vat_enabled:
        if not x.vat_account_id: raise HTTPException(400,"vat_account_id is required when VAT is enabled")
        jlines.append(schemas.JournalLineCreate(account_id=x.vat_account_id,credit=float(vat*dec(order.exchange_rate))))
    j=schemas.JournalCreate(company_id=company_id,entry_no=f"SAL-{x.invoice_no}",entry_date=x.invoice_date,description=f"Sales invoice {x.invoice_no}",source_type="SALES",source_id=inv.id,lines=jlines)
    e=post_journal(db,j); inv.journal_entry_id=e.id; order.status="INVOICED"; db.commit(); db.refresh(inv); return inv

@router.post("/sales/deliveries")
def sales_delivery(x:schemas.SalesDeliveryCreate,db:Session=Depends(get_db)):
    order=db.get(models.SalesOrder,x.sales_order_id)
    if not order: raise HTTPException(404,"sales order not found")
    obj=models.SalesDelivery(sales_order_id=order.id,delivery_no=x.delivery_no,delivery_date=x.delivery_date,warehouse_id=x.warehouse_id)
    db.add(obj); db.flush()
    for l in x.lines:
        q=dec(l.get("quantity",0)); item_id=l.get("item_id")
        if q<=0: raise HTTPException(400,"invalid delivery quantity")
        if item_id:
            balance=inventory_balance(db,item_id,x.warehouse_id) if 'inventory_balance' in globals() else None
            if balance is not None and balance<q: raise HTTPException(400,"insufficient stock")
        db.add(models.SalesDeliveryLine(delivery_id=obj.id,description=l.get("description", ""),item_id=item_id,quantity=q,unit_cost=dec(l.get("unit_cost",0)),batch_no=l.get("batch_no")))
        if item_id:
            db.add(models.InventoryTransaction(item_id=item_id,warehouse_id=x.warehouse_id,transaction_type="OUT",quantity=q,unit_cost=dec(l.get("unit_cost",0)),batch_no=l.get("batch_no")))
    db.commit(); db.refresh(obj); return obj

@router.post("/sales/local-services")
def sales_local_service(x:schemas.SalesLocalServiceCreate, db:Session=Depends(get_db)):
    if x.amount < 0 or x.exchange_rate <= 0: raise HTTPException(400,"invalid service amount/exchange_rate")
    order=db.get(models.SalesOrder,x.sales_order_id)
    if not order: raise HTTPException(404,"sales order not found")
    if order.channel != "LOCAL": raise HTTPException(400,"local services are only allowed for LOCAL sales")
    obj=models.SalesLocalService(sales_order_id=order.id,service_type=x.service_type,description=x.description,amount=x.amount,currency=x.currency,exchange_rate=x.exchange_rate,vat_enabled=False)
    db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/sales/local-services/{sales_order_id}")
def sales_local_services(sales_order_id:str, db:Session=Depends(get_db)):
    rows=db.query(models.SalesLocalService).filter(models.SalesLocalService.sales_order_id==sales_order_id).all()
    total=sum(dec(r.amount)*dec(r.exchange_rate) for r in rows)
    return {"sales_order_id":sales_order_id,"total_egp":float(total),"rows":rows}

@router.post("/sales/other-costs")
def sales_other_cost(x:schemas.SalesOtherCostCreate, db:Session=Depends(get_db)):
    if x.amount < 0 or x.exchange_rate <= 0: raise HTTPException(400,"invalid cost amount/exchange_rate")
    order=db.get(models.SalesOrder,x.sales_order_id)
    if not order: raise HTTPException(404,"sales order not found")
    obj=models.SalesOtherCost(sales_order_id=order.id,cost_type=x.cost_type,description=x.description,amount=x.amount,currency=x.currency,exchange_rate=x.exchange_rate)
    db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/sales/other-costs/{sales_order_id}")
def sales_other_costs(sales_order_id:str, db:Session=Depends(get_db)):
    rows=db.query(models.SalesOtherCost).filter(models.SalesOtherCost.sales_order_id==sales_order_id).all()
    total=sum(dec(r.amount)*dec(r.exchange_rate) for r in rows)
    return {"sales_order_id":sales_order_id,"total_egp":float(total),"rows":rows}

@router.get("/sales/profitability/{sales_order_id}")
def sales_profitability(sales_order_id:str, db:Session=Depends(get_db)):
    order=db.get(models.SalesOrder,sales_order_id)
    if not order: raise HTTPException(404,"sales order not found")
    invoices=db.query(models.SalesInvoice).filter(models.SalesInvoice.sales_order_id==order.id).all()
    revenue=sum(dec(i.subtotal)*dec(order.exchange_rate) for i in invoices)
    deliveries=db.query(models.SalesDelivery).filter(models.SalesDelivery.sales_order_id==order.id).all()
    product_cost=Decimal("0")
    for d in deliveries:
        for l in db.query(models.SalesDeliveryLine).filter(models.SalesDeliveryLine.delivery_id==d.id).all():
            product_cost += dec(l.quantity)*dec(l.unit_cost)
    services=sum(dec(r.amount)*dec(r.exchange_rate) for r in db.query(models.SalesLocalService).filter(models.SalesLocalService.sales_order_id==order.id).all())
    other=sum(dec(r.amount)*dec(r.exchange_rate) for r in db.query(models.SalesOtherCost).filter(models.SalesOtherCost.sales_order_id==order.id).all())
    shipments=db.query(models.Shipment).filter(models.Shipment.sales_order_id==order.id).all()
    freight=sum(dec(x.freight_cost) for x in shipments); transport=sum(dec(x.transport_cost) for x in shipments); insurance=sum(dec(x.insurance_cost) for x in shipments); customs=sum(dec(x.customs_cost) for x in shipments)
    total_cost=product_cost+services+other+freight+transport+insurance+customs
    profit=revenue-total_cost
    return {"sales_order_id":order.id,"channel":order.channel,"revenue_egp":float(revenue),"costs":{"product":float(product_cost),"local_services":float(services),"other":float(other),"freight":float(freight),"transport":float(transport),"insurance":float(insurance),"customs":float(customs),"total":float(total_cost)},"profit_egp":float(profit),"margin_percent":float((profit/revenue*100) if revenue else 0)}

@router.post("/customer-receipts")
def customer_receipt(x:schemas.CustomerReceiptCreate,db:Session=Depends(get_db)):
    if x.amount<=0 or x.exchange_rate<=0: raise HTTPException(400,"invalid receipt")
    obj=models.CustomerReceipt(customer_id=x.customer_id,receipt_no=x.receipt_no,receipt_date=x.receipt_date,currency=x.currency,exchange_rate=x.exchange_rate,amount=x.amount,amount_egp=x.amount*x.exchange_rate,sales_invoice_id=x.sales_invoice_id)
    db.add(obj); db.flush()
    customer=db.get(models.Customer,x.customer_id)
    if not customer or not customer.receivable_account_id: raise HTTPException(400,"customer receivable account required")
    company_id=db.query(models.Company.id).first()[0]
    j=schemas.JournalCreate(company_id=company_id,entry_no=f"REC-{x.receipt_no}",entry_date=x.receipt_date,description=f"Customer receipt {x.receipt_no}",source_type="RECEIPT",source_id=obj.id,lines=[schemas.JournalLineCreate(account_id=x.cash_account_id,debit=float(obj.amount_egp)),schemas.JournalLineCreate(account_id=customer.receivable_account_id,credit=float(obj.amount_egp))])
    post_journal(db,j); db.commit(); db.refresh(obj); return obj

@router.post("/sales/shipments")
def shipment(x:schemas.ShipmentCreate,db:Session=Depends(get_db)):
    if x.shipment_type not in ("LOCAL","EXPORT"): raise HTTPException(400,"shipment_type must be LOCAL or EXPORT")
    order=db.get(models.SalesOrder,x.sales_order_id)
    if not order: raise HTTPException(404,"sales order not found")
    if order.channel!=x.shipment_type: raise HTTPException(400,"shipment type must match sales channel")
    if x.shipment_type=="EXPORT" and not x.destination: raise HTTPException(400,"destination is required for export shipment")
    if x.transport_cost<0: raise HTTPException(400,"transport_cost cannot be negative")
    return crud_create(db,models.Shipment,x)

@router.get("/dashboard/summary")
def dashboard(db:Session=Depends(get_db)):
    return {"structure":"Company > Sector > Farm > Cluster > Greenhouse > CropCycle","sales_channels":["LOCAL","EXPORT"],"companies":db.query(models.Company).count(),"sectors":db.query(models.Sector).count(),"farms":db.query(models.Farm).count(),"clusters":db.query(models.Cluster).count(),"greenhouses":db.query(models.Greenhouse).count(),"crop_cycles":db.query(models.CropCycle).count(),"items":db.query(models.Item).count(),"customers":db.query(models.Customer).count(),"suppliers":db.query(models.Supplier).count(),"accounts":db.query(models.Account).count(),"cost_centers":db.query(models.CostCenter).count(),"journal_entries":db.query(models.JournalEntry).count(),"sales_orders":db.query(models.SalesOrder).count(),"sales_invoices":db.query(models.SalesInvoice).count(),"sales_quotations":db.query(models.SalesQuotation).count(),"sales_deliveries":db.query(models.SalesDelivery).count(),"customer_receipts":db.query(models.CustomerReceipt).count()}

# ---------------- Authentication / Authorization / Audit ----------------
@router.post("/auth/login", response_model=schemas.TokenResponse)
def login(x:schemas.LoginRequest, db:Session=Depends(get_db)):
    user=db.query(models.User).filter_by(username=x.username).first()
    if not user or not user.active or not verify_password(x.password,user.password_hash):
        raise HTTPException(401,"invalid username or password")
    audit(db,user.id,"LOGIN","User",user.id); db.commit()
    return {"access_token":create_token(user),"token_type":"bearer"}

@router.get("/auth/me")
def me(user_id:str=Depends(current_user), db:Session=Depends(get_db)):
    user=db.get(models.User,user_id)
    if not user or not user.active: raise HTTPException(401,"user not found or inactive")
    roles=[r.name for r in db.query(models.Role).join(models.UserRole,models.UserRole.role_id==models.Role.id).filter(models.UserRole.user_id==user.id).all()]
    perms=[p.code for p in db.query(models.Permission).join(models.RolePermission,models.RolePermission.permission_id==models.Permission.id).join(models.UserRole,models.UserRole.role_id==models.RolePermission.role_id).filter(models.UserRole.user_id==user.id).distinct().all()]
    return {"id":user.id,"username":user.username,"full_name":user.full_name,"company_id":user.company_id,"roles":roles,"permissions":perms}

@router.post("/users")
def create_user(x:schemas.UserCreate, db:Session=Depends(get_db), actor:str=Depends(current_user)):
    if db.query(models.User).filter_by(username=x.username).first(): raise HTTPException(409,"username already exists")
    obj=models.User(username=x.username,full_name=x.full_name,password_hash=hash_password(x.password),company_id=x.company_id,active=True)
    db.add(obj); db.flush()
    for role_id in x.role_ids:
        if not db.get(models.Role,role_id): raise HTTPException(404,f"role not found: {role_id}")
        db.add(models.UserRole(user_id=obj.id,role_id=role_id))
    audit(db,actor,"CREATE","User",obj.id,{"username":obj.username}); db.commit(); db.refresh(obj)
    return {"id":obj.id,"username":obj.username,"full_name":obj.full_name,"company_id":obj.company_id}

@router.post("/roles")
def create_role(x:schemas.RoleCreate, db:Session=Depends(get_db), actor:str=Depends(current_user)):
    if db.query(models.Role).filter_by(name=x.name).first(): raise HTTPException(409,"role already exists")
    obj=models.Role(**x.model_dump()); db.add(obj); db.flush(); audit(db,actor,"CREATE","Role",obj.id); db.commit(); db.refresh(obj); return obj

@router.post("/permissions")
def create_permission(x:schemas.PermissionCreate, db:Session=Depends(get_db), actor:str=Depends(current_user)):
    if db.query(models.Permission).filter_by(code=x.code).first(): raise HTTPException(409,"permission already exists")
    obj=models.Permission(**x.model_dump()); db.add(obj); db.flush(); audit(db,actor,"CREATE","Permission",obj.id); db.commit(); db.refresh(obj); return obj

@router.post("/roles/permissions")
def assign_permission(x:schemas.RolePermissionCreate, db:Session=Depends(get_db), actor:str=Depends(current_user)):
    if not db.get(models.Role,x.role_id) or not db.get(models.Permission,x.permission_id): raise HTTPException(404,"role or permission not found")
    if not db.query(models.RolePermission).filter_by(role_id=x.role_id,permission_id=x.permission_id).first(): db.add(models.RolePermission(**x.model_dump()))
    audit(db,actor,"ASSIGN","RolePermission",None,x.model_dump()); db.commit(); return {"status":"ok"}

@router.get("/audit-logs")
def audit_logs(limit:int=100, db:Session=Depends(get_db), actor:str=Depends(current_user)):
    return db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(min(max(limit,1),500)).all()

# ---------------- Idempotent offline synchronization ----------------
def _sync_dispatch(op, db, user_id):
    existing=db.query(models.SyncInbox).filter_by(client_operation_id=op.client_operation_id).first()
    if existing:
        return json.loads(existing.response_json or "{}"), True
    allowed={"/api/farm-operations":(schemas.FarmOperationCreate,farm_operation),"/api/inventory/transactions":(schemas.InventoryCreate,inventory),"/api/companies":(schemas.CompanyCreate,company),"/api/sectors":(schemas.SectorCreate,sector),"/api/farms":(schemas.FarmCreate,farm),"/api/clusters":(schemas.ClusterCreate,cluster),"/api/greenhouses":(schemas.GreenhouseCreate,greenhouse),"/api/crop-cycles":(schemas.CropCycleCreate,cycle)}
    if op.method.upper()!="POST" or op.endpoint not in allowed: raise HTTPException(400,f"sync endpoint not allowed: {op.endpoint}")
    schema,handler=allowed[op.endpoint]
    data=schema.model_validate(op.payload)
    result=handler(data,db)
    # handler may commit; record durable idempotency after successful operation.
    payload=jsonable_encoder(result)
    inbox=models.SyncInbox(client_operation_id=op.client_operation_id,user_id=user_id,endpoint=op.endpoint,method=op.method.upper(),status="COMMITTED",response_json=json.dumps(payload,ensure_ascii=False))
    db.add(inbox); audit(db,user_id,"SYNC","SyncInbox",inbox.id,{"endpoint":op.endpoint,"client_operation_id":op.client_operation_id}); db.commit()
    return payload,False

@router.post("/sync/batch")
def sync_batch(x:schemas.SyncBatch, db:Session=Depends(get_db), user_id:str=Depends(current_user)):
    results=[]
    for op in x.operations:
        try:
            result,replayed=_sync_dispatch(op,db,user_id)
            results.append({"client_operation_id":op.client_operation_id,"status":"SYNCED","replayed":replayed,"result":result})
        except HTTPException as e:
            db.rollback(); results.append({"client_operation_id":op.client_operation_id,"status":"FAILED","replayed":False,"error":e.detail})
        except Exception as e:
            db.rollback(); results.append({"client_operation_id":op.client_operation_id,"status":"FAILED","replayed":False,"error":str(e)})
    return {"processed":len(results),"synced":sum(1 for r in results if r["status"]=="SYNCED"),"failed":sum(1 for r in results if r["status"]=="FAILED"),"results":results}


@router.get("/inventory/card/{item_id}/{warehouse_id}")
def inventory_card(item_id:str, warehouse_id:str, db:Session=Depends(get_db)):
    item=db.get(models.Item,item_id)
    wh=db.get(models.Warehouse,warehouse_id)
    if not item or not wh: raise HTTPException(404,"item or warehouse not found")
    rows=db.query(models.InventoryTransaction).filter(models.InventoryTransaction.item_id==item_id,models.InventoryTransaction.warehouse_id==warehouse_id).order_by(models.InventoryTransaction.transaction_date.asc()).all()
    balance=Decimal("0"); value=Decimal("0"); out=[]
    for r in rows:
        q=dec(r.quantity); c=dec(r.unit_cost)
        if q > 0:
            balance += q; value += q*c
        else:
            avg=(value/balance) if balance else Decimal("0")
            value += q*avg; balance += q
        avg=(value/balance) if balance else Decimal("0")
        out.append({"id":r.id,"date":r.transaction_date,"type":r.transaction_type,"quantity":float(q),"unit_cost":float(c if q>0 else avg),"balance":float(balance),"balance_value":float(value),"average_cost":float(avg),"batch_no":r.batch_no,"expiry_date":r.expiry_date,"source_id":r.id})
    return {"item_id":item_id,"warehouse_id":warehouse_id,"item_name":item.name,"unit":item.unit,"balance":float(balance),"stock_value":float(value),"average_cost":float((value/balance) if balance else 0),"rows":out}

@router.get("/inventory/stock-summary")
def inventory_stock_summary(warehouse_id:str|None=None, db:Session=Depends(get_db)):
    items=db.query(models.Item).filter(models.Item.active==True).all()
    result=[]
    warehouses=db.query(models.Warehouse).all() if not warehouse_id else [db.get(models.Warehouse,warehouse_id)]
    for wh in warehouses:
        if not wh: continue
        for item in items:
            q=dec(db.query(func.coalesce(func.sum(models.InventoryTransaction.quantity),0)).filter(models.InventoryTransaction.item_id==item.id,models.InventoryTransaction.warehouse_id==wh.id).scalar() or 0)
            if q!=0 or dec(item.min_stock)>0 or dec(item.reorder_level)>0:
                status="OK"
                if q <= dec(item.min_stock): status="BELOW_MIN"
                elif q <= dec(item.reorder_level): status="REORDER"
                result.append({"warehouse_id":wh.id,"warehouse":wh.name,"item_id":item.id,"item":item.name,"unit":item.unit,"balance":float(q),"min_stock":float(item.min_stock),"reorder_level":float(item.reorder_level),"status":status})
    return result

@router.get("/inventory/expiring")
def inventory_expiring(days:int=30, db:Session=Depends(get_db)):
    from datetime import date, timedelta
    end=date.today()+timedelta(days=max(0,days))
    rows=db.query(models.InventoryTransaction).filter(models.InventoryTransaction.quantity>0,models.InventoryTransaction.expiry_date!=None,models.InventoryTransaction.expiry_date<=end).order_by(models.InventoryTransaction.expiry_date.asc()).all()
    return [{"id":r.id,"item_id":r.item_id,"warehouse_id":r.warehouse_id,"quantity":float(r.quantity),"batch_no":r.batch_no,"expiry_date":r.expiry_date} for r in rows]

@router.post("/inventory/counts")
def inventory_count(x:schemas.InventoryCountCreate, db:Session=Depends(get_db)):
    if not db.get(models.Warehouse,x.warehouse_id): raise HTTPException(404,"warehouse not found")
    obj=models.InventoryCount(count_no=x.count_no,count_date=x.count_date,warehouse_id=x.warehouse_id,status="DRAFT")
    db.add(obj); db.flush()
    for l in x.lines:
        item=db.get(models.Item,l["item_id"])
        if not item: raise HTTPException(404,"item not found")
        counted=Decimal(str(l.get("counted_quantity",0)))
        if counted < 0: raise HTTPException(400,"counted_quantity must be non-negative")
        system=Decimal(str(db.query(func.coalesce(func.sum(models.InventoryTransaction.quantity),0)).filter(models.InventoryTransaction.item_id==item.id,models.InventoryTransaction.warehouse_id==x.warehouse_id).scalar() or 0))
        unit=Decimal(str(l.get("unit_cost", item.standard_cost or 0)))
        db.add(models.InventoryCountLine(count_id=obj.id,item_id=item.id,batch_no=l.get("batch_no"),expiry_date=l.get("expiry_date"),system_quantity=system,counted_quantity=counted,unit_cost=unit))
    db.commit(); db.refresh(obj)
    return {"id":obj.id,"count_no":obj.count_no,"status":obj.status,"lines":db.query(models.InventoryCountLine).filter_by(count_id=obj.id).all()}

@router.post("/inventory/counts/{count_id}/approve")
def approve_inventory_count(count_id:str, db:Session=Depends(get_db), authorization:str|None=Header(default=None)):
    user_id=current_user(authorization)
    require_permission(db,user_id,"inventory.write")
    obj=db.get(models.InventoryCount,count_id)
    if not obj: raise HTTPException(404,"inventory count not found")
    if obj.status=="APPROVED": return obj
    lines=db.query(models.InventoryCountLine).filter_by(count_id=obj.id).all()
    for l in lines:
        delta=dec(l.counted_quantity)-dec(l.system_quantity)
        if delta==0: continue
        item=db.get(models.Item,l.item_id)
        db.add(models.InventoryTransaction(item_id=l.item_id,warehouse_id=obj.warehouse_id,transaction_type="ADJUSTMENT",quantity=delta,unit_cost=dec(l.unit_cost),total_cost=abs(delta)*dec(l.unit_cost),batch_no=l.batch_no,expiry_date=l.expiry_date,transaction_date=datetime.utcnow()))
    obj.status="APPROVED"; obj.approved_by=user_id; obj.approved_at=datetime.utcnow()
    audit(db,user_id,"APPROVE","InventoryCount",obj.id,{"count_no":obj.count_no})
    db.commit(); db.refresh(obj); return obj

@router.get("/dashboard/kpis")
def dashboard_kpis(company_id:str|None=None, channel:str|None=None, db:Session=Depends(get_db)):
    orders_q=db.query(models.SalesOrder)
    if company_id: orders_q=orders_q.filter(models.SalesOrder.company_id==company_id)
    if channel:
        if channel not in ("LOCAL","EXPORT"): raise HTTPException(400,"channel must be LOCAL or EXPORT")
        orders_q=orders_q.filter(models.SalesOrder.channel==channel)
    orders=orders_q.all(); order_ids=[o.id for o in orders]
    invoices=db.query(models.SalesInvoice).filter(models.SalesInvoice.sales_order_id.in_(order_ids)).all() if order_ids else []
    revenue=sum(dec(i.subtotal)*dec(next(o.exchange_rate for o in orders if o.id==i.sales_order_id)) for i in invoices)
    services=sum(dec(x.amount)*dec(x.exchange_rate) for x in db.query(models.SalesLocalService).filter(models.SalesLocalService.sales_order_id.in_(order_ids)).all()) if order_ids else Decimal("0")
    other=sum(dec(x.amount)*dec(x.exchange_rate) for x in db.query(models.SalesOtherCost).filter(models.SalesOtherCost.sales_order_id.in_(order_ids)).all()) if order_ids else Decimal("0")
    shipments=db.query(models.Shipment).filter(models.Shipment.sales_order_id.in_(order_ids)).all() if order_ids else []
    freight=sum(dec(x.freight_cost) for x in shipments); transport=sum(dec(x.transport_cost) for x in shipments); insurance=sum(dec(x.insurance_cost) for x in shipments); customs=sum(dec(x.customs_cost) for x in shipments)
    deliveries=db.query(models.SalesDelivery).filter(models.SalesDelivery.sales_order_id.in_(order_ids)).all() if order_ids else []
    product_cost=Decimal("0")
    for d in deliveries:
        product_cost += sum(dec(l.quantity)*dec(l.unit_cost) for l in db.query(models.SalesDeliveryLine).filter_by(delivery_id=d.id).all())
    total_cost=product_cost+services+other+freight+transport+insurance+customs
    profit=revenue-total_cost
    crop_cost=db.query(func.coalesce(func.sum(models.CropCost.amount),0)).scalar() or 0
    stock_value=Decimal("0")
    for row in db.query(models.InventoryTransaction.item_id,models.InventoryTransaction.warehouse_id,func.coalesce(func.sum(models.InventoryTransaction.quantity),0)).group_by(models.InventoryTransaction.item_id,models.InventoryTransaction.warehouse_id).all():
        item_id,wh_id,balance=row
        if dec(balance)<=0: continue
        avg=db.query(func.coalesce(func.avg(models.InventoryTransaction.unit_cost),0)).filter(models.InventoryTransaction.item_id==item_id,models.InventoryTransaction.warehouse_id==wh_id,models.InventoryTransaction.quantity>0).scalar() or 0
        stock_value += dec(balance)*dec(avg)
    return {"filters":{"company_id":company_id,"channel":channel},"sales_orders":len(orders),"invoiced_orders":len(set(i.sales_order_id for i in invoices)),"revenue_egp":float(revenue),"product_cost_egp":float(product_cost),"services_egp":float(services),"other_costs_egp":float(other),"freight_egp":float(freight),"transport_egp":float(transport),"insurance_egp":float(insurance),"customs_egp":float(customs),"total_sales_cost_egp":float(total_cost),"profit_egp":float(profit),"margin_percent":float(profit/revenue*100 if revenue else 0),"crop_cost_egp":float(crop_cost),"stock_value_estimated_egp":float(stock_value)}

@router.get("/dashboard/profitability")
def dashboard_profitability(channel:str|None=None, db:Session=Depends(get_db)):
    orders=db.query(models.SalesOrder).all()
    if channel:
        if channel not in ("LOCAL","EXPORT"): raise HTTPException(400,"channel must be LOCAL or EXPORT")
        orders=[o for o in orders if o.channel==channel]
    rows=[]
    for o in orders:
        p=sales_profitability(o.id,db)
        rows.append(p)
    return {"channel":channel,"rows":rows,"count":len(rows)}

@router.get("/employees")
def get_employees(db: Session = Depends(get_db)):
    return db.query(models.Employee).filter(models.Employee.active == True).all()

@router.post("/employees")
def create_employee(x: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    return crud_create(db, models.Employee, x)

@router.get("/attendances")
def get_attendances(date_val: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Attendance)
    if date_val:
        q = q.filter(models.Attendance.date == date_val)
    return q.order_by(models.Attendance.date.desc()).all()

@router.post("/attendances")
def create_attendance(x: schemas.AttendanceCreate, db: Session = Depends(get_db)):
    return crud_create(db, models.Attendance, x)

import io
import csv

@router.post("/accounts/import-csv")
def import_accounts_csv(company_id: str, file_content: str, db: Session = Depends(get_db)):
    """Import chart of accounts from CSV string/file."""
    comp = db.get(models.Company, company_id)
    if not comp:
        raise HTTPException(404, "Company not found")
    
    f = io.StringIO(file_content)
    reader = csv.DictReader(f)
    created_count = 0
    for row in reader:
        code = row.get("code", "").strip()
        name = row.get("name", "").strip()
        account_type = row.get("account_type", "EXPENSE").strip().upper()
        if not code or not name:
            continue
        existing = db.query(models.Account).filter_by(company_id=company_id, code=code).first()
        if not existing:
            obj = models.Account(
                company_id=company_id,
                code=code,
                name=name,
                account_type=account_type,
                is_postable=row.get("is_postable", "true").lower() == "true",
                active=True
            )
            db.add(obj)
            created_count += 1
    db.commit()
    return {"status": "success", "imported_accounts": created_count}

@router.post("/cost-centers/import-csv")
def import_cost_centers_csv(company_id: str, file_content: str, db: Session = Depends(get_db)):
    """Import cost centers from CSV string/file."""
    comp = db.get(models.Company, company_id)
    if not comp:
        raise HTTPException(404, "Company not found")
    
    f = io.StringIO(file_content)
    reader = csv.DictReader(f)
    created_count = 0
    for row in reader:
        code = row.get("code", "").strip()
        name = row.get("name", "").strip()
        center_type = row.get("center_type", "FARM").strip().upper()
        if not code or not name:
            continue
        existing = db.query(models.CostCenter).filter_by(company_id=company_id, code=code).first()
        if not existing:
            obj = models.CostCenter(
                company_id=company_id,
                code=code,
                name=name,
                center_type=center_type,
                active=True
            )
            db.add(obj)
            created_count += 1
    db.commit()
    return {"status": "success", "imported_cost_centers": created_count}
