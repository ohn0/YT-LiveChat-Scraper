from sqlite3 import Timestamp
import requests
from continuation_builder import ContinuationFetcher
from continuation_requestor import ContinuationRequestor
from livechat_requestor import livechatRequestor
from livechat_parser import livechatParser
from player_state import PlayerState
from subsequent_requestor import SubsequentRequestor
import json
from types import SimpleNamespace
import ast

CONTINUATION_FETCH_BASE_URL = "https://www.youtube.com/youtubei/v1/next?"

class LiveChatScraper:
    videoId = None
    continuation = ''
    playerState = None
    contentSet = []
    content = ''
    currentOffsetTimeMsec = 0

    def __init__(self, videoUrl):
        #TODO save videoID from URL
        self.extractVideoID(videoUrl)

    def extractVideoID(self, videoUrl):
        keyStart = videoUrl.find('=')+1
        keyEnd = keyStart+11
        self.videoId = videoUrl[keyStart:keyEnd]

    def getContinuation(self):
        continuationRequestor = ContinuationRequestor(self.videoId)
        continuationRequestor.buildFetcher()
        continuationRequestor.makeRequest()

        self.continuation = continuationRequestor.continuation

    def getInitialLiveChatContents(self):
        liveChatContents = livechatRequestor(self.continuation)
        liveChatContents.buildURL()
        return liveChatContents.getLiveChatData()

    def parseInitialContents(self, initialContents):
        parser = livechatParser('html.parser')
        parser.buildParser(initialContents)
        content = parser.findContent()
        self.continuation = parser.initialContinuation
        self.playerState = PlayerState()
        self.playerState.continuation = self.continuation
        for c in content[1::]:
            self.content += str(c["replayChatItemAction"])
            c["replayChatItemAction"]["batch"] = "INITIAL"
            self.contentSet.append(c["replayChatItemAction"])
        self.playerState.playerOffsetMs = self.findOffsetTimeMsecFinal()
        

    def parseSubsequentContents(self):
        subRequestor = SubsequentRequestor(self.videoId, self.playerState)
        subRequestor.buildFetcher()
        subRequestor.makeRequest()
        content = subRequestor.response["continuationContents"]["liveChatContinuation"]["actions"][1::]
        # print(content.text)
        self.playerState.continuation = subRequestor.updateContinuation(subRequestor.response)
        for c in content:
            c["replayChatItemAction"]["batch"] = "SUBSEQUENT"
            self.content += str(c["replayChatItemAction"])
            self.contentSet.append(c["replayChatItemAction"])
        self.playerState.playerOffsetMs = self.findOffsetTimeMsecFinal()

    def findOffsetTimeMsecFinal(self):
        finalContent = self.contentSet[-1]
        print(finalContent["videoOffsetTimeMsec"])
        return finalContent["videoOffsetTimeMsec"]

    def outputContent(self):
        for c in self.contentSet:
            comment = ''
            timestamp = ''
            author = ''
            # if("replayChatItemAction" in c):
            #     c = c["replayChatItemAction"]
            if("liveChatMembershipItemRenderer" in c["actions"][0]["addChatItemAction"]["item"]):
                timestamp = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["liveChatMembershipItemRenderer"]["timestampText"]["simpleText"] 
                author = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["liveChatMembershipItemRenderer"]["authorName"]["simpleText"]
                comment = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["liveChatMembershipItemRenderer"]["message"]["runs"][0]["text"]
            
            elif("emoji" in c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["message"]["runs"][0]):
                timestamp = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["timestampText"]["simpleText"]
                author = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["authorName"]["simpleText"]
                comment =  c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["message"]["runs"][0]["emoji"]["image"]["accessibility"]["accessibilityData"]["label"]
            else:
                timestamp = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["timestampText"]["simpleText"]
                author = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["authorName"]["simpleText"]
                comment = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["message"]["runs"][0]["text"]
                # print(c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["message"]["runs"][0]["text"])
            print("({0}) {1}: {2}: {3}".format(timestamp, author, comment, c["batch"]))
    
scraper = LiveChatScraper("https://www.youtube.com/watch?v=INA6yz-x4Pk")
scraper.getContinuation()
contents = scraper.getInitialLiveChatContents()
scraper.parseInitialContents(contents)
scraper.parseSubsequentContents()
scraper.outputContent()


# for c in scraper.contentSet:
#     print(str(c))
for c in scraper.contentSet:
    comment = ''
    timeStamp = ''
    author = ''
    # if("replayChatItemAction" in c):
    #     c = c["replayChatItemAction"]
    if("liveChatMembershipItemRenderer" in c["actions"][0]["addChatItemAction"]["item"]):
        timestamp = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["liveChatMembershipItemRenderer"]["timestampText"]["simpleText"] 
        author = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["liveChatMembershipItemRenderer"]["authorName"]["simpleText"]
        comment = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["liveChatMembershipItemRenderer"]["message"]["runs"][0]["text"]
    
    elif("emoji" in c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["message"]["runs"][0]):
        timestamp = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["timestampText"]["simpleText"]
        author = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["authorName"]["simpleText"]
        comment =  c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["message"]["runs"][0]["emoji"]["image"]["accessibility"]["accessibilityData"]["label"]
    else:
        timestamp = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["timestampText"]["simpleText"]
        author = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["authorName"]["simpleText"]
        comment = c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["message"]["runs"][0]["text"]
        # print(c["actions"][0]["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["message"]["runs"][0]["text"])
    # print("({0}) {1}: {2}: {3}".format(timestamp, author, comment, c["batch"]))
# with open('v.json', 'w', encoding='utf-8') as writer:
#     writer.write



'''
    step 1: 
        Grab initial continuation value  using continuation builder and requestors, these will require the videoId
    
    step 2:
        Use initial continuation value to fetch first livechat request using livechat_requestor and livechat_parser.
        The first livechat contents will be returned in a script embedded in a HTML document, which is why the parser is required
        to extract the contents.

        Ensure the continuation value updates after the livechat_requestor is done executing. The continuation value will update 
        each time a request is made as it is used to keep track of where we are on the video's timeline.

    step 3:
        Use subsequent_requestor and start a loop to grab each block of livechat data. Each time a request is made, the continuation
        value MUST be update to ensure the next obtained block of data does not contain any duplicates or missed values.
'''

# scraper = LiveChatScraper('https://www.youtube.com/watch?v=EezhXfjR1_k')