from fastapi import FastAPI
from .api import router
app=FastAPI(title='Agri ERP', version='2.1.0')
app.include_router(router,prefix='/api')
@app.get('/health')
def health(): return {'status':'ok','version':'2.1.0'}
