from datetime import date, datetime, timedelta, timezone
from threading import RLock
from uuid import uuid4
from app.services import simplify_transfers
_lock=RLock(); _items=[]; _sent={}
def _emit(key, group_id, recipient_id, kind, title, message):
 now=datetime.now(timezone.utc)
 with _lock:
  if key in _sent and now-_sent[key] < timedelta(days=1): return
  _sent[key]=now; _items.append({"id":uuid4().hex,"group_id":group_id,"recipient_id":recipient_id,"type":kind,"title":title,"message":message,"created_at":now.isoformat(),"read":False})
def check_group(storage, group_id, user_id):
 names={u.id:u.name for u in storage.list_users(group_id)}
 for t in simplify_transfers(storage, group_id):
  if t.from_user_id==user_id: _emit((group_id,user_id,t.to_user_id,'debt'),group_id,user_id,'debt','Непогашенный долг',f'У вас есть долг {t.amount:.2f} ₽ перед {names.get(t.to_user_id,"участником")}.')
 ops=storage.list_operations(group_id); start=date.today().replace(day=1); spent=sum(o.amount for o in ops if o.type.value=='expense' and o.operation_date>=start); days=(date.today()-start).days+1
 if days>=7 and spent>0: _emit((group_id,user_id,'budget'),group_id,user_id,'budget','Прогноз бюджета',f'По текущему темпу расходы могут составить около {spent/days*30:.0f} ₽. Проверьте необязательные траты.')
def list_notifications(group_id, recipient_id):
 with _lock: return [dict(x) for x in _items if x['group_id']==group_id and x['recipient_id']==recipient_id]
