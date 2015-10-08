# -*- coding: utf-8 -*-

import json
import re
import urllib2
import base64
import math
import numpy as np
import sys
from goose import Goose

if len(sys.argv) < 4:
    print 'Enter all the 3 arguments'
    sys.exit()

handlestopword = open('stopwords.txt','r')
stopwords = handlestopword.readline().split(',')
handlestopword.close()
dictionary = []

def checkStopWord(word):    
    if word in stopwords:
        return True
    return False    
    
def insertDictionary(word):
    word = word.lower()
    if checkStopWord(word)==False:
        if word not in dictionary:
            if word!='':
                dictionary.append(word)

accountKey = sys.argv[1]
accountKeyEnc = base64.b64encode(accountKey + ':' + accountKey)
headers = {'Authorization': 'Basic ' + accountKeyEnc}
try:
    precision = float(sys.argv[2])
except ValueError:
    print "Please enter a value between 0 and 1 as the second argument" 
    sys.exit()
query = sys.argv[3:len(sys.argv)]
newPrecision = 0
while True:
    prevPrecision = newPrecision
    dictionary = []
    queryUrl = '%20'.join(query)
    queryUrl = '%27' + queryUrl + '%27'
    bingUrl = 'https://api.datamarket.azure.com/Bing/Search/Web?Query='+queryUrl+'&$top=10&$format=json'
    
    # connecting to bing api and getting response of the query passed in the URL
    req = urllib2.Request(bingUrl, headers = headers)
    response = urllib2.urlopen(req)
    content = response.read()
    json_result = json.loads(content)
       
    titleList = []
    descriptionList = []
    urlList = []
    
    for result in json_result['d']['results']:
        titleList.append(result['Title'].lower().encode('ascii','ignore').decode('ascii'))
        descriptionList.append(result['Description'].lower().encode('ascii','ignore').decode('ascii'))
        urlList.append(result['Url'])
    
    print "Parameters:"
    print "Client Key = "+accountKey
    print "Query = "+' '.join(query)
    print "Precision = "+`precision`
    print 'URL: '+bingUrl
    print 'Total number of results : 10'
    print 'Bing Search Results:'
    print '============================='
    
    relevantCount = 0
    nonRelevantCount = 0
    relevantDocs = []
    nonRelevantDocs = []
    
    for i in range(0,10):
        print "Result "+`i+1`
        print '['
        print ' URL: '+urlList[i]
        print ' Title: '+titleList[i]
        print ' Summary: '+descriptionList[i]
        print ']'
            
        while True:
            output = raw_input('Relevant[Y/N]? ')
            if output.lower() not in ('y','n'):
                print("Enter either Y or N")
                continue
            else:
                break
        
        if output.lower() == "y":
            relevantCount = relevantCount + 1
            relevantDocs.append(i)
        else: 
            nonRelevantCount = nonRelevantCount + 1
            nonRelevantDocs.append(i)
    
    print '======================='
    print 'FEEDBACK SUMMARY'
    print "Query = "+' '.join(query)
    newPrecision = relevantCount*0.1
    print 'Precision '+`newPrecision`
    if newPrecision == 0:
        print 'Below desired precision, but can no longer augment the query'
        break
    
    if newPrecision < prevPrecision:
        print 'Precision reduced'
        break
    
    if newPrecision < precision:
        print 'Still below the desired precision of '+`precision`
        print 'Indexing result....'
        print 'Indexing result....'
        # Forming an array containing all the words(after eliminating punctuations) in each title
        titles = []
        for title in titleList:
            titles.append(re.split(' |, |\. |; |: |\(|\) |\? ',title)) 
        
        # Forming an array containing all the words(after eliminating punctuations) in each description
        descriptions = []
        for description in descriptionList:
            descriptions.append(re.split(' |, |\. |; |: |\(|\) |\? |\)',description)) 
        
        # Inserting all the word obtained from every title and description in the dictionary using stopword elimination
        for sentence in titles:
            for word in sentence:
                insertDictionary(word)
        
        for sentence in descriptions:
            for word in sentence:
                insertDictionary(word)


        termFrequency = []
        documentFrequency = []
              
        # computing the document frequency of every word in the dictionary      
        for word in dictionary:
            count = 0
            for i in range(0,len(urlList)):
                if word in titles[i] or word in descriptions[i]:
                    count = count + 1
            documentFrequency.append(count)        
        
        # computing the term frequency of every word in the dictionary for each document
        for i in range(0,len(urlList)):
            doc = []
            for word in dictionary:
                count = titles[i].count(word) + descriptions[i].count(word)
                doc.append(count)        
            termFrequency.append(doc)
        
        # computing weights for every word in every document (forming a vector for every document)
        weights = termFrequency   
        for doc in weights:
            for j in range(0,len(dictionary)):
                doc[j] = doc[j]*math.log(len(dictionary)/documentFrequency[j])
        
        # normalization of every weight vector
        for doc in weights:
            norm = np.linalg.norm(np.array(doc))    
            for j in range(0,len(dictionary)):
                doc[j] = doc[j]/norm
        
        # compute the vector of the original query        
        queryWeights = []
        for word in dictionary:
            if word in query:
                queryWeights.append(1)
            else:
                queryWeights.append(0)
        
        alpha = 1
        beta = 0.75
        gamma = 0.15
        
        queryVector = alpha*np.array(queryWeights)
        
        # compute the normalized sum of all the relevant document vectors 
        relevantDocSum = np.zeros(len(dictionary)); 
        for index in relevantDocs:
            vector = np.array(weights[index])
            relevantDocSum = relevantDocSum + vector
        relevantDocSum = relevantDocSum/len(relevantDocs)*beta
        
        # compute the normalized sum of all the non-relevant document vectors 
        nonRelevantDocSum = np.zeros(len(dictionary)); 
        for index in nonRelevantDocs:
            vector = np.array(weights[index])
            nonRelevantDocSum = nonRelevantDocSum + vector
        nonRelevantDocSum = nonRelevantDocSum/len(nonRelevantDocs)*gamma
        
        # applying Rocchio algorithm
        modifiedQueryVector = queryVector + relevantDocSum - nonRelevantDocSum
        
        # eliminating negetive terms from modified query vector
        for i in range(0,len(modifiedQueryVector)):
            if modifiedQueryVector[i] < 0:
                modifiedQueryVector[i] = 0
                
        newQuery = []                
        
        # extracting top 5 words with maximum weights after applying rocchio
        max5 = []
        max5words = []        
        for i in range (len(query)+1,len(query)+6):
            max5.append(np.partition(modifiedQueryVector,-i)[-i])
            max5words.append(dictionary[np.argpartition(modifiedQueryVector,-i)[-i]])
        
        #print max5words
        #print max5
        
        # this is a special and a rare case when the weights of top 5 words are not very distinguishable,
        # in which case we crawl through the entire content of the relevant docs to obtain the most 
        # frequently occuring word amongst these 5 words in the contents of the relevant results
        if (max5[0]-max5[2])/max5[0]<0.2:
            wordCount = dict((word,0) for word in max5words)
            
            # crawling through content of relevant docs and finding normalized count of the above 5 words 
            for relevantIndex in relevantDocs:
                url = urlList[relevantIndex]
                print 'crawling through : ' + url
                g= Goose()
                article = g.extract(url=url)
                x = ''.join(article.cleaned_text[:])
                x = x.encode('ascii','ignore').decode('ascii')
                pageWords = re.split(' |, |\. |; |: |:|\(|\) |\? |\n', x)
                
                for word in pageWords:
                    word = word.lower()
                    if word in wordCount:
                        wordCount[word] = wordCount[word] + 1.0/len(pageWords)
            print wordCount

            values = []
            for word in max5words:
                if word in wordCount:
                    values.append(wordCount[word])
            values = np.array(values)        
            
            #obtaining the indices of the words with maximum count in the content of the docs
            ind3 = np.argpartition(values, -3)[-3]
            ind2 = np.argpartition(values, -2)[-2]
            ind1 = np.argpartition(values, -1)[-1]
            
            # formulating the query to be augmented, here we append the word with max count
            newQuery.append(max5words[ind1])
            
            # deciding if second word should be appended to the new query 
            if 0.8*(values[ind1]-values[ind2]) < values[ind2] - values[ind3]:
                newQuery.append(max5words[ind2])
        else:
            #obtaining the indices of the words with maximum weights after the words already in the query
            ind3 = np.argpartition(modifiedQueryVector, -(len(query)+3))[-(len(query)+3)]
            ind2 = np.argpartition(modifiedQueryVector, -(len(query)+2))[-(len(query)+2)]
            ind1 = np.argpartition(modifiedQueryVector, -(len(query)+1))[-(len(query)+1)]
            
            #print dictionary[ind1] + ' ' + `modifiedQueryVector[ind1]`
            #print dictionary[ind2] + ' ' + `modifiedQueryVector[ind2]`
            #print dictionary[ind3] + ' ' + `modifiedQueryVector[ind3]`
    
            # formulating the query to be augmented, here we append the word with max weight
            newQuery.append(dictionary[ind1])
            
            # deciding if second word should be appended to the new query 
            if 0.8*(modifiedQueryVector[ind1]-modifiedQueryVector[ind2]) < modifiedQueryVector[ind2] - modifiedQueryVector[ind3]:
                newQuery.append(dictionary[ind2])

        print 'Augmenting by '+' '.join(newQuery)        
        query = query + newQuery
    else:
        print 'Desired precision reached,DONE'
        break