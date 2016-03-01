import re
import math
from naivebayesianstorage import NaiveBayesianStorage
from collections import OrderedDict

class NaiveBayesian:

    # min token length for it to be taken into consideration '''
    min_token_length = 3
    # max token length for it to be taken into consideration '''
    max_token_length = 15
    
    def __init__(self, db, login = None, password =None, server =None, use_sqlite = True, reset = False):
        self.ignore_list = []
        self.include_list = []
        
        self.nbs = NaiveBayesianStorage( db, use_sqlite=use_sqlite, user=login, pwd=password, server=server, reset=reset )
        
    def categorize( self, document):
        ''' categorize a document.
        Get list of categories in which the document can be categorized
        with a score for each category.

            @return array keys = category ids, values = scores
            @param string document
        '''
        scores = {}
        categories = self.nbs.getCategories()
        tokens = self._getTokens( document )
        
        # calculate the score in each category
        total_words = 0
        ncat = 0
        
        for category in categories:
            data = categories[category]
            total_words += data['word_count']
            ncat += 1
            
        for category in categories:
            data = categories[category]
            scores[category] = data['probability'];
            # small probability for a word not in the category
            # maybe putting 1.0 as a 'no effect' word can also be good
            small_proba = 1.0/((data['word_count']+1)*20000)
            
            for token in tokens:
                count = tokens[token]
                if self.nbs.wordExists( token ):
                    word = self.nbs.getWord( token, category )
                    if word['count'] > 0 and data['word_count'] > 0:
                        proba = float(word['count']) / data['word_count']
                    else:
                        proba = small_proba
                    scores[category] *= pow(proba, count) * pow(total_words/ncat, count)
                    # pow( total_words/ ncat, count) is here to avoid underflow.
        
        return self._rescale(scores);
        
    def categorise( self, document ):
        ''' proper spelling '''
        return self.categorize( document )

    def train( self, docid, category_id, content ):
        ''' training against a document.
        Set a document as being in a specific category. The document becomes a reference
        and is saved in the table of references. After a set of training is done
        the updateProbabilities() function must be run.

            @see updateProbabilities()
            @see untrain()
            @return bool success
            @param string document id, must be unique
            @param string category_id the category id in which the document should be
            @param string content of the document
        '''
    
        # check if docid already exists
        doc = self.nbs.getReference(docid)
        if doc!=None and len(doc)>0:
            return False
    
        # standardise the strings
        docid = re.sub('<[^>]*>', '', docid.strip())
        docid = docid.replace(' ', '')
        category_id = re.sub('<[^>]*>', '', category_id.strip())
        category_id = category_id.replace(' ', '')
        content = content.strip()
        
        if category_id =="":
            return False
        if content == "":
            return False
        
        # go through each word
        tokens = self._getTokens(content)
        for token, count in tokens.iteritems():
            self.nbs.updateWord( token, count, category_id )
        self.nbs.saveReference( docid, category_id, content)
        return True

    def untrain( self, doc_id ):
        ''' untraining of a document.
        To remove just one document from the references.

            @see updateProbabilities()
            @see untrain()
            @return bool success
            @param string document id, must be unique
        '''
        ref = self.nbs.getReference( doc_id )
        tokens = self._getTokens( ref['content'] )
        for token, count in tokens.iteritems():
            self.nbs.removeWord( token, count, ref['category_id'] )
        self.nbs.removeReference( doc_id )
        return True

    def _rescale( self, scores ):
        ''' rescale the results between 0 and 1.
        
            @author Ken Williams, ken@mathforum.org 
            @see categorize()
            @return array normalized scores (keys => category, values => scores)
            @param array scores (keys => category, values => scores)
        '''
        # Scale everything back to a reasonable area in 
        # logspace (near zero), un-loggify, and normalize
        total = 0.0
        max   = 0.0
        
        scores = OrderedDict(sorted(scores.items(), key=lambda t: t[1], reverse=True))
        
        for cat in scores:
            score = scores[cat]
            if( score >= max ):
                max = score
        
        for cat in scores:
            score = scores[cat]
            scores[cat] = math.exp( score - max)
            total += pow( scores[cat], 2)
        
        total = math.sqrt( total )
        
        for cat in scores:
            scores[cat] = scores[cat]/total
            
        return scores
    

    def updateProbabilities(self):
        ''' update the probabilities of the categories and word count.
        This function must be run after a set of training

            @see train()
            @see untrain()
            @return bool success
        '''
        return self.nbs.updateProbabilities()

    def getIgnoreList( self ):
        ''' Get the list of token to ignore.
            @return array ignore list
        '''
        return ['the', 'that', 'you', 'for', 'and', 'of', 'income', 
            'incoming', 'resources', 'receipts', 'receivable', 
            'received', 'from', 'charitable', 'activities', 
            'other', 'generating', 'funds', 'voluntary', 
            'net', 'assets','funds','expenditure','total', 
            'expended', 'costs', 'cost']

    def getIncludeList( self ):
        ''' Get the list of token to include.
            @return array ignore list
        '''
        return ['mr']

    def _getTokens( self, string ):
        ''' get the tokens from a string

            @author James Seng. [http://james.seng.cc/] (based on his perl version)

            @return array tokens
            @param  string the string to get the tokens from
        '''
    
        rawtokens = []
        tokens = {}
        string = self._cleanString( string )
        
        if( len(self.ignore_list) == 0 ):
            self.ignore_list = self.getIgnoreList()
        if( len(self.include_list) == 0 ):
            self.include_list = self.getIncludeList()
            
        rawtokens = re.split("[^-_A-Za-z0-9]+", string)
        
        # remove some tokens
        for token in rawtokens:
            token = token.strip()
            
            if (not(('' == token)                        or
                  (len(token) < self.min_token_length) or
                  (len(token) > self.max_token_length) or
                  (re.match('[0-9]+$', token))   or
                  (token in self.ignore_list)
                )                                      or
                  (token in self.include_list)
                ):
                if( tokens.has_key(token) ):
                    tokens[token] += 1
                else:
                    tokens[token] = 1
        
        return tokens

    def _cleanString( self, string ):
        ''' clean a string from the diacritics

            @author Antoine Bajolet [phpdig_at_toiletoine.net]
            @author SPIP [http://uzine.net/spip/]

            @return string clean string
            @param  string string with accents
        '''
        string = string.strip()
        return string.lower()
    
    
    def addcat( self, cat = False, catname = False ):
        ''' add a category to the database

            @author Antoine Bajolet [phpdig_at_toiletoine.net]
            @author SPIP [http://uzine.net/spip/]

            @return bool sucess
            @param  string slug for category
            @param  string name of category
        '''
        return self.nbs.addcat( cat, catname)
    
    
    def remcat( self, cat = False ):
        ''' remove a category from the database

            @author Antoine Bajolet [phpdig_at_toiletoine.net]
            @author SPIP [http://uzine.net/spip/]

            @return bool sucess
            @param  string slug for category
            @param  string name of category
        '''
        return self.nbs.remcat( cat )
    
    def getCategories( self ):
        return self.nbs.getCategories()
        
        	
    def bestMatch( self, document, threshold = -0.01 ):
        ''' get the best match for a doc
        
            @author David Kane (david.kane@ncvo.org.uk)

            The score of the match is stored in $this->last_score for reference

            @return string|bool best match category (no 
            @param string document
            @param float threshold for returning a match default is -0.01 (ie no threshold)
        '''
        document = self._cleanString( document )
        self.last_score = None
        scores = self.categorize( document )
        options = 0
        best_match = False
        for cat in scores:
            score = scores[cat]
            
            # if the score is positive, and the first one, then let's use it
            # the --threshold could be adjusted to give a higher threshold for chosing the answer (at the moment there is no barrier)
            if( score >= threshold and options==0 ):
                best_match = ( cat, score )
                options += 1
        return best_match
        
'''
  ***** BEGIN LICENSE BLOCK *****
   This file is part of PHP Naive Bayesian Filter.

   The Initial Developer of the Original Code is
   Loic d'Anterroches [loic_at_xhtml.net].
   Portions created by the Initial Developer are Copyright (C) 2003
   the Initial Developer. All Rights Reserved.

   Contributor(s):

   PHP Naive Bayesian Filter is free software; you can redistribute it
   and/or modify it under the terms of the GNU General Public License as
   published by the Free Software Foundation; either version 2 of
   the License, or (at your option) any later version.

   PHP Naive Bayesian Filter is distributed in the hope that it will
   be useful, but WITHOUT ANY WARRANTY; without even the implied
   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
   See the GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with PHP Naive Bayesian Filter; if not, write to the Free Software
   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

   Alternatively, the contents of this file may be used under the terms of
   the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
   in which case the provisions of the LGPL are applicable instead
   of those above.

  ***** END LICENSE BLOCK *****
'''