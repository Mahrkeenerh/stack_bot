import praw, datetime, json, xmltodict, re, StackWrap, Logger, requests
from time import sleep
from threading import Thread


with open("config.json") as config_file:

    config_json = json.load(config_file)

    userAgent = config_json['userAgent']
    cID = config_json['cID']
    cSC = config_json['cSC']
    userN = config_json['userN']
    userP = config_json['userP']

reddit = praw.Reddit(user_agent=userAgent, 
    client_id=cID, 
    client_secret=cSC, 
    username=userN, 
    password=userP)

forum_list = []
queue_replies = []

time_locker = False

footer = "\n\n^(This action was performed automagically.) [^(info_post)](https://www.reddit.com/user/stack_bot/comments/pel66h/info_post/) ^(Did I make a mistake?) [^(contact)](https://www.reddit.com/user/stack_bot/comments/pel563/contact/) ^(or reply: error)"


# get list of forums from internet
def get_forum_list():

    global forum_list

    response = requests.get("https://stackexchange.com/feeds/sites")
    full_dict = xmltodict.parse(response.content)

    forum_list = [i["id"].replace("http://", "") for i in full_dict["feed"]["entry"]]
    save()


# load list
def load():

    global forum_list

    try:
        get_forum_list()
        Logger.log_message("Got forum list")

    except:
        Logger.log_error("En error occured while getting forum list")

        with open("forum_list.json") as json_file:
            data = json.load(json_file)
            forum_list = data["forum_list"]


# save list
def save():

    global forum_list

    with open("forum_list.json", "w") as json_file:
        json.dump({"forum_list": forum_list}, json_file)


# save current time
def save_time():

    global time_locker

    while time_locker:
        Logger.log_message("Sleeping for time.txt")
        sleep(1)
    
    time_locker = True

    with open("time.txt", "w") as file:
        print(datetime.datetime.now().strftime('%y.%m.%d %H:%M:%S'), file=file)
    
    time_locker = False


# load last known time
def load_time():

    global time_locker

    while time_locker:
        Logger.log_message("Sleeping for time.txt")
        sleep(1)
    
    time_locker = True

    try:
        with open("time.txt") as file:
            current_time = datetime.datetime.strptime(file.readline().strip(), '%y.%m.%d %H:%M:%S')
            time_locker = False

            return current_time
    
    except FileNotFoundError:
        time_locker = False

        save_time()

        return load_time()


# return link, site, id and type
def get_info(body):

    global forum_list

    posts = []

    for item in re.sub("[\[\]\(\)\{\}\'\"]", " ", body).split():
        for forum in forum_list:
            if forum in item:
                link = item.strip()
                if link not in [i["link"] for i in posts]:
                    posts.append({"link": link})
                    break

    for i in range(len(posts) - 1, -1, -1):
        contents = posts[i]["link"].split("/")

        try:
            posts[i]["id"] = int(contents[4])
            posts[i]["type"] = contents[3][0]
            posts[i]["site"] = contents[2]

        except:
            del posts[i]

    return posts    


# replace triple backticks ``` with four spaces magically
def fix_code_blocks(text):

    arr = text.split("```")

    for i in range(1, len(arr), 2):
        arr[i] = "    " + arr[i].replace("\n", "\n    ")
    
    return "".join(arr).replace("    ", "     ")


# respond to comment or post with general stuff
def respond_question(entry, post_raw):

    global footer

    # there's no answer
    if not post_raw["is_answered"]:
        owner_link = None if "link" not in post_raw["owner"] else post_raw["owner"]["link"]
        header = "The [question](%s) **\"%s\"** by [%s](%s) doesn't currently have any answers. Question contents:\n\n" % (post_raw["share_link"], post_raw["title"], post_raw["owner"]["display_name"], owner_link)
        message = ">" + fix_code_blocks(post_raw["body_markdown"]).replace("\n", "\n>")

        entry.reply(header + message + footer)

        return
    
    # marked answer
    if "accepted_answer_id" in post_raw:
        for answer in post_raw["answers"]:
            if answer["answer_id"] == post_raw["accepted_answer_id"]:
                owner_link = None if "link" not in answer["owner"] else answer["owner"]["link"]
                header = "The [question](%s) **\"%s\"** has got an accepted [answer](%s) by [%s](%s) with the score of %d:\n\n" % (post_raw["share_link"], post_raw["title"], answer["share_link"], answer["owner"]["display_name"], owner_link, answer["score"])
                message = ">" + fix_code_blocks(answer["body_markdown"]).replace("\n", "\n>")

                entry.reply(header + message + footer)

                return

    # no marked answer
    else:
        answer = max(post_raw["answers"], key=lambda x: x["score"])
        owner_link = None if "link" not in answer["owner"] else answer["owner"]["link"]
        header = "The [question](%s) **\"%s\"** doesn't have an accepted answer. The [answer](%s) by [%s](%s) is the one with the highest score of %d:\n\n" % (post_raw["share_link"], post_raw["title"], answer["share_link"], answer["owner"]["display_name"], owner_link, answer["score"])
        message = ">"  + fix_code_blocks(answer["body_markdown"]).replace("\n", "\n>")

        entry.reply(header + message + footer)

        return


# respond to comment or post with specific answer
def respond_answer(entry, post_raw, answer_id):

    global footer

    for answer in post_raw["answers"]:
        if answer["answer_id"] == answer_id:
            owner_link = None if "link" not in answer["owner"] else answer["owner"]["link"]
            header = "[Answer](%s) by [%s](%s) with the score of %d:\n\n" % (answer["share_link"], answer["owner"]["display_name"], owner_link, answer["score"])
            message = ">" + fix_code_blocks(answer["body_markdown"]).replace("\n", "\n>")

            entry.reply(header + message + footer)

            return


# respond to comment or post saying there's something wrong with your link
def respond_error(entry, link):

    global footer

    message = "There's something wrong with the link you've provided:\n\n" + link

    entry.reply(message + footer)


# check comment and post contents, match it and respond
def process_entry(entry, body):

    lowercase_body = body.lower()
    for post in get_info(lowercase_body):
        
        # ignore - not a question or answer
        if post["type"] not in "qa":
            continue

        if post["type"] == "q":
            post_raw = StackWrap.get_question(post["id"], post["site"])

            # there's something wrong here
            if "error_id" in post_raw:
                respond_error(entry, post["link"])
            else:
                respond_question(entry, post_raw)

        # if post["type"] == "a":
        #     post_raw = StackWrap.get_answer(post["id"], post["site"])

        #     # there's something wrong here
        #     if "error_id" in post_raw:
        #         respond_error(entry, post["link"])
        #     else:
        #         respond_answer(entry, post_raw)

        save_time()


# search comments
def check_comments():

    while True:
        try:
            Logger.log_message("Starting comments")

            subreddit = reddit.subreddit("all")
            last_time = load_time()

            for comment in subreddit.stream.comments():
                comment_time = datetime.datetime.fromtimestamp(comment.created_utc)

                # only check new comments not made by the bot
                if comment_time > last_time and comment.author != userN:
                    process_entry(comment, str(comment.body))

        # reddit is not responding or something, idk, error - wait, try again
        except:
            Logger.log_error("En error occured with comments")
            sleep(60)


# search submissions
def check_submissions():

    while True:
        try:
            Logger.log_message("Starting submissions")

            subreddit = reddit.subreddit("all")
            last_time = load_time()

            for submission in subreddit.stream.submissions():
                submission_time = datetime.datetime.fromtimestamp(submission.created_utc)

                # only check new submissions not made by the bot
                if submission_time > last_time and submission.author != userN:
                    process_entry(submission, str(submission.selftext))

        # reddit is not responding or something, idk, error - wait, try again
        except:
            Logger.log_error("En error occured with submissions")
            sleep(60)


# check replies and message u/Mahrkeenerh (me)
def check_inbox():

    Logger.log_message("Starting inbox")

    while True:
        try:
            new_mentions = []

            for mention in reddit.inbox.unread():
                new_mentions.append(mention)
                lowercase_body = mention.body.lower()

                if "error" in lowercase_body or "report" in lowercase_body or "bad" in lowercase_body:
                    Logger.log_message("Bad bot :(", "https://reddit.com" + mention.context, mention.body)

            reddit.inbox.mark_read(new_mentions)

        # reddit is not responding or something, idk, error - wait, try again
        except:
            Logger.log_error("En error occured with inbox")
            sleep(60)


# # search subreddits
# def check_subreddits():

#     global queue_comments

#     while True:
#         try:
#             log_message("Starting subreddits")

#             subreddit = reddit.subreddit("all")
#             last_time = load_time()

#             for submission in subreddit.stream.submissions():

#                 submission_time = datetime.datetime.fromtimestamp(submission.created_utc)

#                 # only check new posts
#                 if submission_time > last_time:
#                     lowercase_body = str(submission.selftext).lower()




#                     # loop through all watch lists
#                     for item in watch_list:
#                         if item[0] == submission.subreddit:
#                             if submission.author != item[1] and check_keywords(item, lowercase_body, lowercase_title):
#                                 message = ['notify_me_bot: %s' % (item[0]), 'You requested a notification, here is your post:\n\n%s\n\nTo cancel this subreddit notifications, reply: cancel' % (submission.permalink)]
                                
#                                 # try to send message, or garbage
#                                 try:
#                                     save_time()
#                                     reddit.redditor(item[1]).message(message[0], message[1])
#                                 except:
#                                     queue_directs.append([item[1], message])

#         # reddit is not responding or something, idk, error - wait, try again
#         except:
#             log_error("En error occured with subreddits")
#             sleep(60)




# # resend messages that didn't go through
# def garbage_collection():

#     global queue_mentions, queue_directs

#     while True:
#         pos = 0

#         while pos < len(queue_mentions) and queue_mentions:
#             try:
#                 pos += 1
#                 queue_mentions[pos - 1][0].reply(queue_mentions[pos - 1][1])
#                 queue_mentions.remove(queue_mentions[pos - 1])
#                 pos -= 1

#             except:
#                 if "RATELIMIT" in "".join(traceback.format_exception(*sys.exc_info())):
#                     continue

#                 else:
#                     log_error("Message didn't still go through", "\nAuthor:", queue_directs[pos - 1][0].author, "\nBody:", queue_directs[pos - 1][0].body, "\nReply body:", queue_mentions[pos - 1][1])

#         pos = 0

#         while pos < len(queue_directs) and queue_directs:
#             try:
#                 pos += 1
#                 reddit.redditor(queue_directs[pos - 1][0]).message(queue_directs[pos - 1][1][0], queue_directs[pos - 1][1][1])
#                 queue_directs.remove(queue_directs[pos - 1])
#                 pos -= 1

#             except:
#                 if "RATELIMIT" in "".join(traceback.format_exception(*sys.exc_info())):
#                     continue

#                 else:
#                     log_error("Message didn't still go through", "\nUser:", queue_directs[pos - 1][0], "\nObject:", queue_directs[pos - 1][1][0], "\nReply body:", queue_directs[pos - 1][1][1])

#                 if "USER_DOESNT_EXIST" in "".join(traceback.format_exception(*sys.exc_info())):
#                     queue_directs.remove(queue_directs[pos - 1])
#                     purge_users()

#         sleep(60)


Logger.log_message("Starting")

load()
sleep(0.1)
Thread(target=check_comments, args=()).start()
sleep(0.1)
Thread(target=check_submissions, args=()).start()
sleep(0.1)
Thread(target=check_inbox, args=()).start()
sleep(0.1)

# garbage_collection()
