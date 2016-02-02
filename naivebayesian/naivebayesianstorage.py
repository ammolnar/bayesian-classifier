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

import re
import MySQLdb as mdb

''' Access to the storage of the data for the filter.

To avoid dependency with respect to any database, this class handle all the
access to the data storage. You can provide your own class as long as
all the methods are available. The current one rely on a MySQL database.

methods:
    - array getCategories()
    - bool  wordExists(string $word)
    - array getWord(string $word, string $categoryid)

'''
class NaiveBayesianStorage:

    def __init__(self, user, pwd, server, dbname, set = False, reset = False):
        self.set = set
        self.con = mdb.connect( server, user, pwd, dbname)
        self.category_cache = {}
        self.word_cache = {}
        if( self.con ):
            if(set):
                self.set = set
                if(reset):
                    self.resetTables()
                self.createTables()

    ''' Create the tables needed.
        @return bool successs
    '''
    def createTables( self ):
        sql = []

        sql.append("""CREATE TABLE IF NOT EXISTS `nb_{set}_categories` (
                  category_id varchar(250) NOT NULL default '',
                  probability double NOT NULL default '0',
                  word_count bigint(20) NOT NULL default '0',
                  `description` varchar(255) DEFAULT NULL,
                  PRIMARY KEY  (category_id)
                )""")

        sql.append("""CREATE TABLE IF NOT EXISTS `nb_{set}_references` (
                  `id` varchar(250) NOT NULL DEFAULT '',
                  `category_id` varchar(250) NOT NULL DEFAULT '',
                  `content` text NOT NULL,
                  PRIMARY KEY (`id`),
                  KEY `category_id` (`category_id`)
                )""")

        sql.append("""CREATE TABLE IF NOT EXISTS `nb_{set}_wordfreqs` (
                  `word` varchar(250) NOT NULL DEFAULT '',
                  `category_id` varchar(250) NOT NULL DEFAULT '',
                  `count` bigint(20) NOT NULL DEFAULT '0',
                  PRIMARY KEY (`word`,`category_id`)
                )""")

        successCount = 0

        for s in sql:
            s = s.format( set= self.set )
            cur = self.con.cursor(mdb.cursors.DictCursor)

            if( cur.execute( s ) ):
                successCount += 1

        if(successCount==3):
            return true

        return False

    ''' Remove existing tables and data.
        @return bool successs
    '''
    def resetTables( self ):
        sql = []

        sql.append("""DROP TABLE IF EXISTS `nb_{set}_categories`""")
        sql.append("""DROP TABLE IF EXISTS `nb_{set}_references`""")
        sql.append("""DROP TABLE IF EXISTS `nb_{set}_wordfreqs`""")

        successCount = 0

        for s in sql:
            s = s.format( set= self.set )
            cur = self.con.cursor(mdb.cursors.DictCursor)

            if( cur.execute( s ) ):
                successCount += 1

        if(successCount==3):
            return true

        return False

    ''' get the list of categories with basic data.
        @return array key = category ids, values = array(keys = 'probability', 'word_count', 'description')
    '''
    def getCategories( self ):
        if self.category_cache:
            return self.category_cache
        else:
            sql = "SELECT * FROM nb_{set}_categories".format( set= self.set )

            cur = self.con.cursor(mdb.cursors.DictCursor)
            rs = cur.execute( sql )
            rows = cur.fetchall()

            for row in rows:
                self.category_cache[row['category_id']] = {
                        'probability': row['probability'],
                        'word_count': row['word_count'],
                        'description': row['description']
                    }

            return self.category_cache

    ''' see if the word is an already learnt word.
        @return bool
        @param string word
    '''
    def wordExists( self, word):
        if word in self.word_cache:
            return True
        else:
            cur = self.con.cursor(mdb.cursors.DictCursor)
            sql = "SELECT * FROM nb_{set}_wordfreqs WHERE word=%s".format( set= self.set )
            rs = cur.execute( sql, (word,) )
            return cur.rowcount>0

    ''' get details of a word in a category.
        @return array ('count' => count)
        @param  string word
        @param  string category id
    '''
    def getWord( self, word, category_id):
        if self.word_cache.get(word, {}).has_key(category_id):
            return self.word_cache[word][category_id]
        else:
            self.word_cache[word] = {}

        cur = self.con.cursor(mdb.cursors.DictCursor)
        sql = "SELECT * FROM nb_{set}_wordfreqs WHERE word=%s AND category_id=%s".format( set= self.set )
        rs = cur.execute( sql, (word,category_id) )
        word_count = 0
        if(cur.rowcount>0):
            row = cur.fetchone()
            word_count = row['count']

        self.word_cache[word][category_id] = {'count': word_count}

        return self.word_cache[word][category_id]

    ''' update a word in a category.
    If the word is new in this category it is added, else only the count is updated.

        @return bool success
        @param string word
        @param int    count
        @paran string category id
    '''
    def updateWord( self, word, count, category_id, catname = None):
        if word=="":
            return
        oldWord = self.getWord( word, category_id )
        cur = self.con.cursor(mdb.cursors.DictCursor)

        # add the category if it's not already there
        self.addcat( category_id, catname )

        if (0 == oldWord['count']):
            sql = "REPLACE INTO nb_{set}_wordfreqs (word, category_id, count) VALUES (%s,%s,%s)".format( set= self.set )
            values = ( word, category_id, str(count) )
        else:
            sql = "UPDATE nb_{set}_wordfreqs SET count = count + %s WHERE category_id = %s AND word = %s".format( set= self.set )
            values = ( str(count), category_id, word )

        cur.execute( sql, values )
        self.con.commit()

    ''' remove a word from a category.

        @return bool success
        @param string word
        @param int  count
        @param string category id
    '''
    def removeWord( self, word, count, category_id ):
        if word=="":
            return
        oldWord = self.getWord( word, category_id )
        cur = self.con.cursor(mdb.cursors.DictCursor)

        if (0 != oldWord['count'] and 0 >= (oldWord['count']-count)):
            sql = "DELETE FROM nb_{set}_wordfreqs WHERE word = %s AND category_id = %s".format( set= self.set )
            values = ( word, category_id )
        else:
            sql = "UPDATE nb_{set}_wordfreqs SET count -= %s WHERE category_id = %s AND word = %s".format( set= self.set )
            values = ( count, category_id, word )

        cur.execute( sql, values )

    ''' update the probabilities of the categories and word count.
    This function must be run after a set of training

        @return bool sucess
    '''
    def updateProbabilities( self ):
        # first update the word count of each category
        cur = self.con.cursor(mdb.cursors.DictCursor)
        sql = "SELECT category_id, SUM(count) AS total FROM nb_{set}_wordfreqs WHERE 1 GROUP BY category_id".format( set= self.set )
        rs = cur.execute( sql )
        rows = cur.fetchall()

        total_words = 0

        for row in rows:
            total_words += row['total']

        if (total_words == 0):
            sql = "UPDATE nb_{set}_categories SET word_count=0, probability=0 WHERE 1".format( set= self.set )
            return True

        for row in rows:
            proba = row['total'] / total_words
            row_sql = "UPDATE nb_{set}_categories SET word_count = %s, probability= %s WHERE category_id = %s".format( set= self.set )
            row_query = cur.execute( row_sql, (row["total"],proba, row["category_id"]) )
            self.con.commit()

        return True

    ''' save a reference in the database.

        @return bool success
        @param  string reference if, must be unique
        @param  string category id
        @param  string content of the reference
    '''
    def saveReference( self, doc_id, category_id, content):
        sql = "INSERT INTO nb_{set}_references (id, category_id, content) VALUES (%s,%s,%s)".format( set= self.set )
        cur = self.con.cursor(mdb.cursors.DictCursor)
        cur.execute( sql, (doc_id,category_id, content) )
        self.con.commit()

    ''' get a reference from the database.

        @return array  reference( category_id => ...., content => ....)
        @param  string id
    '''
    def getReference( self, doc_id):

        cur = self.con.cursor(mdb.cursors.DictCursor)
        sql = "SELECT * FROM nb_{set}_references WHERE id = %s".format( set= self.set )
        rs = cur.execute( sql, (doc_id,) )
        if( cur.rowcount==0):
            return {}

        return cur.fetchone()

    ''' remove a reference from the database

        @return bool sucess
        @param  string reference id
    '''
    def removeReference( self, doc_id):
        cur = self.con.cursor(mdb.cursors.DictCursor)
        sql = "DELETE FROM nb_{set}_references WHERE id = %s".format( set= self.set )
        rs = cur.execute( sql, (doc_id,) )
        self.con.commit()

    ''' add a category to the database

        @author Antoine Bajolet [phpdig_at_toiletoine.net]
        @author SPIP [http:#uzine.net/spip/]

        @return bool sucess
        @param  string slug for category
        @param  string name of category
    '''
    def addcat( self, cat = False, catname = False):
        if(not(cat)):
            return False

        if(not(catname)):
            catname = cat

        cat = re.sub('<[^>]*>', '', cat.strip())
        cat = cat.replace(' ', '')

        catname = re.sub('<[^>]*>', '', catname.strip())
        catname = catname.replace(' ', '')

        if(len(cat)==0):
            return False

        cur = self.con.cursor(mdb.cursors.DictCursor)
        sql = "INSERT IGNORE INTO nb_{set}_categories (category_id, description) VALUES (%s,%s)".format( set= self.set )
        cur.execute( sql, (cat, catname) )

        return True

    ''' remove a category to the database

        @author Antoine Bajolet [phpdig_at_toiletoine.net]
        @author SPIP [http:#uzine.net/spip/]

        @return bool sucess
        @param  string slug for category
        @param  string name of category
    '''
    def remcat( self, cat = False):
        if(not(cat)):
            return False

        cat = re.sub('<[^>]*>', '', cat.strip())
        cat = cat.replace(' ', '')

        if(len(cat)==0):
            return False

        cur = self.con.cursor(mdb.cursors.DictCursor)
        cur.execute("DELETE FROM nb_{set}_categories WHERE category_id=%s".format( set= self.set ), (cat,) )
        cur.execute("DELETE FROM nb_{set}_references WHERE category_id=%s".format( set= self.set ), (cat,) )
        cur.execute("DELETE FROM nb_{set}_wordfreqs  WHERE category_id=%s".format( set= self.set ), (cat,) )
        self.updateProbabilities()

        return True


    ''' check whether a set exists

        @author David Kane [david.kane_at_ncvo-vol.org.uk]

        @return bool sucess
        @param  string name of the set
    '''
    def set_exists( self, set = False):

        if(not(set)):
            return False

        cur = self.con.cursor(mdb.cursors.DictCursor)
        sql = "SHOW TABLES LIKE 'nb_{set}_%'".format( set= self.set )
        rs = cur.execute( sql )
        return cur.rowcount==3
