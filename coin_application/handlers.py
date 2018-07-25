from coin_application.users import dao
from lib.baseweb import get, post
from lib.utils import _
from settings import choices

#search coin info
@get('/coinai/get/user/survey/state')
async def survey_state(request):

    result = {"error": 0, "data": "", "message": ""}
    state = 0
    user_id = request.__user__.get("referId", "")
    count = await dao.findUserNumber(user_id)
    if count:
        state = 1
    result['data'] = {"state": state}
    return result

#add user survey
@post('/coinai/add/user/survey')
async def add_user_survey(request, *, option_one, option_two, option_three):

    result = {"error": 0, "data": "", "message":""}
    user_id = request.__user__.get("referId", "")
    nickname = request.__user__.get("referName", "")
    head_image_url = request.__user__.get("headImageUrl", "")
    name = request.__user__.get("loginName", "")
    language = request.__user__.get("language", "en")

    count = await dao.findUserNumber(user_id)
    if count:
        result["error"] = 418
        result["message"] = "The Account have been investigated!"
    else:
        option_one_val = choices["option_one"].get(int(option_one), 1)
        option_two_val = choices["option_two"].get(int(option_two), 1)
        option_three_val = choices["option_three"].get(int(option_three),1)
        score = float(option_one_val) + float(option_two_val) + float(option_three_val)
        ratio = float(float(option_one_val)/50 + float(option_two_val)/10 + float(option_three_val)*10)/100.0
        await dao.saveUser(user_id, name, nickname, head_image_url, option_one, option_two, option_three, score, ratio)
        result["message"] = _("0_ADD_SUCCESSFUL", language)  # "Added successfully."

    return result