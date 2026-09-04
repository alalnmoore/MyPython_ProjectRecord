from fastapi import APIRouter

from model import DiaryCreate, DiaryResponse

love_router = APIRouter(prefix="/love")
emo_db = {}
global_diary_id =1
@love_router.get("/welcome")
def welcome():
    return {"message": "欢迎使用情绪记录API"}

# 进行情绪的记录并返回当前记录的情绪对象信息，json返回
@love_router.post("/diary")
def emotion_record(emo:DiaryCreate):
    global global_diary_id
    emo_message = DiaryResponse(
        diary_id = global_diary_id,
        user_id = emo.user_id,
        content = emo.content,
        scene =emo.scene
    )
    emo_db[global_diary_id] = emo_message
    global_diary_id+=1
    return emo_message

# 根据id查询某个情绪的对象json返回
@love_router.get("/diary/{diary_id}")
def query_diary(diary_id:int):
    return emo_db[diary_id]

# 分页查询情绪列表
@love_router.get("/diaries")
def query_all_diaries(page:int,page_size:int):
    emo_list =list(emo_db.values())
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    return emo_list[start_index:end_index]





