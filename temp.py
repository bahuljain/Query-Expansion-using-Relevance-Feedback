# -*- coding: utf-8 -*-

import json
import re
import urllib2
import base64
import math
import numpy as np
import sys

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
        
        #print ' '.join(dictionary)

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

        ind = np.argsort(modifiedQueryVector)
        ind1 = ind[ind.size - len(query) -1]
        ind2 = ind[ind.size - len(query) -2]
        ind3 = ind[ind.size - len(query) -3]   
        
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