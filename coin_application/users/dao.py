
from coin_application.users.models import User


async def findUserNumber(user_id):

    count = await User.findNumber("count(id)", where="user_id=?", args=[user_id])
    return count


async def findUserByIds(user_ids=[]):

    range_str = "("
    for _ in user_ids:
        range_str += "?,"
    users = await User.findAll(where='user_id in %s)' % range_str.rstrip(","), args=user_ids)
    return users


async def findAllUser(user_id):

    user = await User.findAll(where="user_id=?", args=[user_id,])
    if user:
        user = user[0]
    return user


async def saveUser(user_id, name, nickname, head_image_url, option_one, option_two, option_three, score, ratio, state=0):

    obj = await findAllUser(user_id)
    if obj:
        obj.head_image_url = head_image_url
        obj.nickname = nickname
        res = await obj.update()
    else:
        user = User(user_id=user_id, name=name, nickname=nickname, head_image_url=head_image_url,option_one=option_one,
                    option_two=option_two, option_three=option_three, score=score, ratio=ratio, state=state)
        res = await user.save()
    return res