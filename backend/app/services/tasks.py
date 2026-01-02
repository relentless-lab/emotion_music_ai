from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.task import TaskRecord
from app.schemas.tasks import TaskDetail, TaskStatus, TaskType


def create_task(
    db: Session,
    *,
    user_id: int | None,
    task_type: TaskType,
    input_payload: Dict[str, Any],
    auto_complete: bool = True,
    result: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
) -> TaskRecord:
  task_id = str(uuid4())
  status = TaskStatus.completed if auto_complete else TaskStatus.pending
  record = TaskRecord(
      id=task_id,
      user_id=user_id,
      type=task_type,
      status=status,
      input=input_payload,
      result=result if auto_complete else None,
      message=message,
  )
  db.add(record)
  db.commit()
  db.refresh(record)
  return record


def set_status(db: Session, task_id: str, status: TaskStatus, message: Optional[str] = None) -> Optional[TaskRecord]:
  record = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
  if not record:
    return None
  record.status = status
  if message is not None:
    record.message = message
  record.updated_at = datetime.utcnow()
  db.commit()
  db.refresh(record)
  return record


def get_task(db: Session, task_id: str, expected_type: TaskType | None = None) -> Optional[TaskRecord]:
  record = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
  if not record:
    return None
  if expected_type and record.type != expected_type:
    return None
  return record


def list_tasks(db: Session, *, user_id: int | None = None, status: TaskStatus | None = None) -> List[TaskRecord]:
  query = db.query(TaskRecord)
  if user_id is not None:
    query = query.filter(TaskRecord.user_id == user_id)
  if status:
    query = query.filter(TaskRecord.status == status)
  return query.order_by(TaskRecord.created_at.desc()).all()


def complete_task(db: Session, task_id: str, result: Dict[str, Any], message: Optional[str] = None) -> Optional[TaskRecord]:
  record = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
  if not record:
    return None
  record.status = TaskStatus.completed
  record.result = result
  record.message = message
  record.updated_at = datetime.utcnow()
  db.commit()
  db.refresh(record)
  return record


def fail_task(db: Session, task_id: str, message: str) -> Optional[TaskRecord]:
  record = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
  if not record:
    return None
  record.status = TaskStatus.failed
  record.message = message
  record.updated_at = datetime.utcnow()
  db.commit()
  db.refresh(record)
  return record


def to_task_detail(record: TaskRecord) -> TaskDetail:
  return TaskDetail(
      id=record.id,
      type=record.type,
      status=record.status,
      created_at=record.created_at,
      updated_at=record.updated_at,
      input=record.input,
      result=record.result,
      message=record.message,
  )
