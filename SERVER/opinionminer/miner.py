import nltk
from nltk.corpus import wordnet
from nltk.corpus import stopwords
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize,word_tokenize,regexp_tokenize

import requests
import signal
import sys
import codecs
from functools import partial
import time

from TwitterSearch import *

# register a signal handler so that we can exit early
def signal_handler(comments,fname,signal, frame):
    print('KeyboardInterrupt')
    if fname is not None:
        write_comments_to_file(comments,'{}.txt'.format(fname))
    sys.exit(0)
    
def write_comments_to_file(comments,filename):
    print('\n')
    if len(comments) == 0:
        print('No comments to write.')
        return

    with codecs.open(filename, 'w', encoding='utf-8') as f:
        for comment in comments:
            f.write(comment + '\n**FB_COMMENT**\n')

    print('Wrote {} comments to {}'.format(len(comments), filename))

"""
limit - max num of comments to load. if 0 then load all.

"""
def grab_fb_comments(graph_api_version,access_token,user_id,post_id,limit = 200,filename = None):
    
    comments = []
    
    #signal.signal(signal.SIGINT, partial(signal_handler,comments,filename))
    url = 'https://graph.facebook.com/{}/{}_{}/comments'.format(graph_api_version, user_id, post_id)
    
    r = requests.get(url, params={'access_token': access_token})
    while True:
        data = r.json()

        # catch errors returned by the Graph API
        if 'error' in data:
            raise Exception(data['error']['message'])

        # append the text of each comment into the comments list
        for comment in data['data']:
            # remove line breaks in each comment
            text = comment['message'].replace('\n', ' ')
            comments.append(text)

        sys.stdout.write('\rGot {} comments, total: {}'.format(len(data['data']), len(comments)))

        # check if we have enough comments
        if 0 < limit <= len(comments):
            break

        # check if there are more comments
        if 'paging' in data and 'next' in data['paging']:
            while True:
                try:
                    r = requests.get(data['paging']['next'])
                    break
                except:
                    time.sleep(1)
                    
        else:
            break

    # save the comments to a file
    if filename is not None:
        write_comments_to_file(comments,'{}.txt'.format(filename))
    
    return comments

def find_sentiment(sid,para,features,overall_sentiment,features_sentiment,score):
    
    para = para.lower()
    sentences = sent_tokenize(para)
    
    #paragraph sentiment
    
    ss = sid.polarity_scores(para)
    
    overall_sentiment[score(ss['compound'])] += 1
  
    tmp_features = [i for i in features]
    
    for sentence in sentences: 
        wrds = word_tokenize(sentence)
        english_stops = set(stopwords.words('english'))
        wrds = [word for word in wrds if word not in english_stops] #remove stop words and punctuations
        keys_found = []
        for tff in tmp_features:
            # we want to find a word not an extension of one. eg. if we search 'hair' the if will find 'chair' valid.
            if sentence.lower().find(' ' + tff.lower() + ' ') > -1:
                keys_found.append(tff) 
        c = 0
        dd = 10
        tmp_str = {}
        tmp_indx = []
        if len(keys_found) > 1:
            
            tmp = [0 for i in wrds]
            for wrd in wrds:
                ss = sid.polarity_scores(wrd)
                tmp[c] = ss['compound']
                if wrd in keys_found:
                    tmp[c] = dd
                    tmp_indx.append(c)
                    tmp_str[dd] = wrd
                    dd *= 2
                    keys_found.remove(wrd)
                c += 1
           
            # estimate which keyword belongs to which neg or pos sentiment
            while 0.0 in tmp: tmp.remove(0.0)
            tmpshift = [tmp[i] for i in range(1,len(tmp))]
            comb = zip(tmp,tmpshift)
            filterd = [i for i in comb if (i[0] <= 1 and i[1] > 1) or (i[0] > 1 and i[1] <= 1)]
            for fil in filterd:
                val = ''
                keywrd = ''
                if fil[0] <= 1: val = score(fil[0])
                if fil[0] > 1: keywrd = tmp_str[fil[0]]
                if fil[1] <= 1: val = score(fil[1])
                if fil[1] > 1: keywrd = tmp_str[fil[1]]
                features_sentiment[keywrd][val] += 1
                try:
                    tmp_features.remove(keywrd)
                except:
                    continue


        elif len(keys_found) == 1: 
            ss = sid.polarity_scores(sentence)
            features_sentiment[keys_found[0]][score(ss['compound'])] += 1
            tmp_features.remove(keys_found[0])
        
    return overall_sentiment,features_sentiment

def fetch_fb_sentiment(access_token,user_id,post_id,features,limit = 800):
    result = {}
    graph_api_version = 'v2.12'
    score = lambda x: 'Neu' if x >= -0.2 and x <= 0.2 else ('Pos' if x > 0.2 else 'Neg')
    comments = grab_fb_comments(graph_api_version,access_token,user_id,post_id,limit = limit,filename = None)
    total_comm = len(comments)
    overall_sentiment = {'Neg' : 0,'Neu' : 0,'Pos' : 0}
    sid = SentimentIntensityAnalyzer()
    # sentence analysis
    features_sentiment = {}
    for feat in features:
        features_sentiment[feat] = {'Neg' : 0,'Neu' : 0,'Pos' : 0}

    # Load comments from FB or from File
    for comment in comments:
        overall_sentiment,features_sentiment = find_sentiment(sid,comment,features,overall_sentiment,features_sentiment,score)


    pos_sent = (overall_sentiment['Pos'] / (total_comm * 1.)) * 100
    neu_sent = (overall_sentiment['Neu'] / (total_comm * 1.)) * 100
    neg_sent = (overall_sentiment['Neg'] / (total_comm * 1.)) * 100


    print('Number Of Comments: {}'.format(total_comm))
    print('\nOverall Sentiment: POSITIVE  ({}) {}% | NEUTRAL ({}) {}% | NEGATIVE ({}) {}%'.format(overall_sentiment['Pos'],pos_sent,overall_sentiment['Neu'],neu_sent,overall_sentiment['Neg'],neg_sent))
    print('\nFeature Sentiment: {}'.format(features_sentiment))
    
    result['Number Of Comments'] = total_comm
    result['Overall Sentiment'] = overall_sentiment
    result['Feature Sentiment'] = features_sentiment
    
    return result

def fetch_file_sentiment(handler,features):
    score = lambda x: 'Neu' if x >= -0.2 and x <= 0.2 else ('Pos' if x > 0.2 else 'Neg')
    overall_sentiment = {'Neg' : 0,'Neu' : 0,'Pos' : 0}
    sid = SentimentIntensityAnalyzer()
    # sentence analysis
    features_sentiment = {}
    total_comments = -1
    result = {}
    
    for feat in features:
        features_sentiment[feat] = {'Neg' : 0,'Neu' : 0,'Pos' : 0}
    
    for comment in handler:
        if total_comments == -1:
            total_comments = 0
            continue
        overall_sentiment,features_sentiment = find_sentiment(sid,comment,features,overall_sentiment,features_sentiment,score)
        total_comments += 1
    
    pos_sent = (overall_sentiment['Pos'] / (total_comments * 1.)) * 100
    neu_sent = (overall_sentiment['Neu'] / (total_comments * 1.)) * 100
    neg_sent = (overall_sentiment['Neg'] / (total_comments * 1.)) * 100


    print('Number Of Comments: {}'.format(total_comments))
    print('\nOverall Sentiment: POSITIVE  ({}) {}% | NEUTRAL ({}) {}% | NEGATIVE ({}) {}%'.format(overall_sentiment['Pos'],pos_sent,overall_sentiment['Neu'],neu_sent,overall_sentiment['Neg'],neg_sent))
    print('\nFeature Sentiment: {}'.format(features_sentiment))
    
    result['Number Of Comments'] = total_comments
    result['Overall Sentiment'] = overall_sentiment
    result['Feature Sentiment'] = features_sentiment
    
    return result

def fetch_twitter_sentiment(keywords,features,limit = 300):
    score = lambda x: 'Neu' if x >= -0.2 and x <= 0.2 else ('Pos' if x > 0.2 else 'Neg')
    overall_sentiment = {'Neg' : 0,'Neu' : 0,'Pos' : 0}
    sid = SentimentIntensityAnalyzer()
    result = {}
    
    # sentence analysis
    features_sentiment = {}
    for feat in features:
        features_sentiment[feat] = {'Neg' : 0,'Neu' : 0,'Pos' : 0}
        
    tso = TwitterSearchOrder()
    tso.set_keywords(keywords)# let's define all words we would like to have a look for
    tso.set_language('en') 
    #tso.set_count(5)

    tso.set_include_entities(False) # and don't give us all those entity information
    
    # it's about time to create a TwitterSearch object with our secret tokens
    ts = TwitterSearch(
        consumer_key = '5xVeLnwKq4YfrKlSU7a92GN4z',
        consumer_secret = 'gZp4FZ4Bxie26HsSTSZQ7uApnzVeTSqIC8SMLLcnvEHSneORXh',
        access_token = '836845218280402950-MaKkAY5RoGYj4fakMirbT70zdVhFoH8',
        access_token_secret = 'p29Zbrt2YYFkWco4EAgpIPkJ7mCblrKmdWQrXi4RdpW9Z',
     )
    querystr = tso.create_search_url() + '&tweet_mode=extended'
    tso2 = TwitterSearchOrder()
    tso2.set_search_url(querystr)
    tso2.set_locale('en')
    
    
    tweet_counter = 1
    try:
        for tweet in ts.search_tweets_iterable(tso2):
            overall_sentiment,features_sentiment = find_sentiment(sid,tweet['full_text'],features,overall_sentiment,features_sentiment,score)
            sys.stdout.write('\rProcessed Tweets: {}'.format(tweet_counter))
            tweet_counter += 1
            if tweet_counter > int(limit):
                break

    except TwitterSearchException as e: # take care of all those ugly errors if there are some
        print(e)
    
    pos_sent = (overall_sentiment['Pos'] / (tweet_counter * 1.)) * 100
    neu_sent = (overall_sentiment['Neu'] / (tweet_counter * 1.)) * 100
    neg_sent = (overall_sentiment['Neg'] / (tweet_counter * 1.)) * 100


    print('\nNumber Of Comments: {}'.format(tweet_counter))
    print('\nOverall Sentiment: POSITIVE  ({}) {}% | NEUTRAL ({}) {}% | NEGATIVE ({}) {}%'.format(overall_sentiment['Pos'],pos_sent,overall_sentiment['Neu'],neu_sent,overall_sentiment['Neg'],neg_sent))
    print('\nFeature Sentiment: {}'.format(features_sentiment))
    
    result['Number Of Comments'] = tweet_counter
    result['Overall Sentiment'] = overall_sentiment
    result['Feature Sentiment'] = features_sentiment
    
    return result

