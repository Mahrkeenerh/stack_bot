import requests


# get complex json with question and answers
def get_question(question_id, site):

    url = "https://api.stackexchange.com/2.3/questions/" + str(question_id) + "?site=" + site + "&filter=!)e)ZsVzQujHkTsD9ivDwPAo367LKsBlWODSV6KKAfLiz740f"

    response = requests.get(url=url).json()
    
    if "error_id" in response:
        return response

    return response["items"][0]


# # get complex json with question and answer
# def get_answer(answer_id, site):

#     url = "https://api.stackexchange.com/2.3/questions/" + str(answer_id) + "?site=" + site + "&filter=!)e)ZsVzQujHkTsD9ivDwPAo367LKsBlWODSV6KKAfLiz740f"

#     response = requests.get(url=url).json()
    
#     if "error_id" in response:
#         return response

#     return response["items"][0]
