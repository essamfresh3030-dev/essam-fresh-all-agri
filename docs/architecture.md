# Agri ERP Architecture v0.7

## Backend
FastAPI → SQLAlchemy → SQLite/PostgreSQL

Core layers:
- master data: company/sector/farm/cluster/greenhouse/crop cycle
- operations: irrigation/fertilization/pesticide/labor/harvest/waste
- inventory + accounting integration
- local/export sales
- authentication and authorization
- audit log
- offline synchronization

## Authentication
JWT access token لمدة 12 ساعة.
Passwords تستخدم PBKDF2-HMAC-SHA256 مع salt عشوائي.

## Offline sync
العميل يحفظ الطلب في `sync_queue` عندما لا يتوفر الخادم. عند الاتصال:
1. يرسل batch إلى `/api/sync/batch`.
2. الخادم يتحقق من `client_operation_id`.
3. إذا كانت العملية جديدة ينفذها ويسجلها في `sync_inbox`.
4. إذا كانت موجودة يعيد النتيجة السابقة بدلاً من إنشاء سجل جديد.

## Cost traceability
Material / production operation → Crop Cycle → Greenhouse → Cluster → Farm → Sector → Cost Center → Accounting.

## PostgreSQL
`DATABASE_URL` يدعم PostgreSQL مباشرة، وملف `docker-compose.yml` يوفر بيئة تطوير مشتركة.
