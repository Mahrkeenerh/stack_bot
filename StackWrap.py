import requests


# get complex json with question and answers
def get_question(question_id, site):

    url = "https://api.stackexchange.com/2.3/questions/" + str(question_id) + "?site=" + site + "&filter=!)e)ZsVzQujHkTsD9ivDwPAo367LKsBlWODSV6KKAfLiz740f"

    response = requests.get(url=url).json()
    
    if "error_id" in response:
        return response

    return response["items"][0]


# get just the question id
def get_question_id(answer_id, site):

    url = "https://api.stackexchange.com/2.3/answers/" + str(answer_id) + "?site=" + site + "&filter=!peu5Q)ZLpQQGX"

    response = requests.get(url=url).json()

    if "error_id" in response:
        return response

    return response["items"][0]["question_id"]
