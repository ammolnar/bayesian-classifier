import re
import sqlite3

class NaiveBayesianStorage:
    ''' Access to the storage of the data for the filter.

    To avoid dependency with respect to any database, this class handle all the
    access to the data storage. You can provide your own class as long as
    all the methods are available. The current one rely on a MySQL database.

    methods:
        - array getCategories()
        - bool  wordExists(string $word)
        - array getWord(string $word, string $categoryid)

    '''

    def __init__(self, dbname, user=None, pwd=None, server=None, use_sqlite=True, reset = False):
        if use_sqlite:
            self.con = sqlite3.connect( dbname )
            self.dbtype = "sqlite"
        else:
            import MySQLdb as mdb
            self.con = mdb.connect( server, user, pwd, dbname)
            self.dbtype = "mysql"
        self.category_cache = {}
        self.word_cache = {}
        if( self.con ):
            if(reset):
                self.resetTables()
            self.createTables()
                
    def get_db_cursor(self):
        '''
        Get a database cursor
        '''
        if self.dbtype=="mysql":
            cur = self.con.cursor(mdb.cursors.DictCursor)
        else:
            self.con.row_factory = sqlite3.Row
            cur = self.con.cursor()
        return cur

    def createTables( self ):
        ''' Create the tables needed.
            @return bool successs
        '''
        sql = []

        sql.append("""CREATE TABLE IF NOT EXISTS `categories` (
                  category_id varchar(250) NOT NULL default '',
                  probability double NOT NULL default '0',
                  word_count bigint(20) NOT NULL default '0',
                  `description` varchar(255) DEFAULT NULL,
                  PRIMARY KEY  (category_id)
                )""")

        sql.append("""CREATE TABLE IF NOT EXISTS `references` (
                  `id` varchar(250) NOT NULL DEFAULT '',
                  `category_id` varchar(250) NOT NULL DEFAULT '',
                  `content` text NOT NULL,
                  PRIMARY KEY (`id`)
                )""")

        sql.append("""CREATE TABLE IF NOT EXISTS `wordfreqs` (
                  `word` varchar(250) NOT NULL DEFAULT '',
                  `category_id` varchar(250) NOT NULL DEFAULT '',
                  `count` bigint(20) NOT NULL DEFAULT '0',
                  PRIMARY KEY (`word`,`category_id`)
                )""")

        successCount = 0

        for s in sql:
            cur = self.get_db_cursor()

            if( cur.execute( s ) ):
                successCount += 1

        if(successCount==3):
            return True

        return False

    def resetTables( self ):
        ''' Remove existing tables and data.
            @return bool successs
        '''
        sql = []

        sql.append("""DROP TABLE IF EXISTS `categories`""")
        sql.append("""DROP TABLE IF EXISTS `references`""")
        sql.append("""DROP TABLE IF EXISTS `wordfreqs`""")

        successCount = 0

        for s in sql:
            cur = self.get_db_cursor()

            if( cur.execute( s ) ):
                successCount += 1

        if(successCount==3):
            return True

        return False

    def getCategories( self ):
        ''' get the list of categories with basic data.
            @return array key = category ids, values = array(keys = 'probability', 'word_count', 'description')
        '''
        if self.category_cache:
            return self.category_cache
        else:
            sql = "SELECT * FROM categories"

            cur = self.get_db_cursor()
            rs = cur.execute( sql )
            rows = cur.fetchall()

            for row in rows:
                self.category_cache[row['category_id']] = {
                        'probability': row['probability'],
                        'word_count': row['word_count'],
                        'description': row['description']
                    }

            return self.category_cache

    def wordExists( self, word):
        ''' see if the word is an already learnt word.
            @return bool
            @param string word
        '''
        if word in self.word_cache:
            return True
        else:
            cur = self.get_db_cursor()
            sql = "SELECT * FROM wordfreqs WHERE word=?"
            cur.execute( sql, (word,) )
            results = cur.fetchall()
            return len(results)>0

    def getWord( self, word, category_id):
        ''' get details of a word in a category.
            @return array ('count' => count)
            @param  string word
            @param  string category id
        '''
        if self.word_cache.get(word, {}).has_key(category_id):
            return self.word_cache[word][category_id]
        else:
            self.word_cache[word] = {}

        cur = self.get_db_cursor()
        sql = "SELECT * FROM wordfreqs WHERE word=? AND category_id=?"
        rs = cur.execute( sql, (word,category_id) )
        word_count = 0
        row = cur.fetchone()
        if(row):
            word_count = row['count']
            self.word_cache[word][category_id] = {'count': word_count}
            return self.word_cache[word][category_id]
            
        return {'count':word_count}

    def updateWord( self, word, count, category_id, catname = None):
        ''' update a word in a category.
        If the word is new in this category it is added, else only the count is updated.

            @return bool success
            @param string word
            @param int    count
            @paran string category id
        '''
        if word=="":
            return
        oldWord = self.getWord( word, category_id )
        cur = self.get_db_cursor()

        # add the category if it's not already there
        self.addcat( category_id, catname )

        if (0 == oldWord['count']):
            sql = "REPLACE INTO wordfreqs (word, category_id, count) VALUES (?,?,?)"
            values = ( word, category_id, str(count) )
            self.word_cache[word][category_id] = {'count': count}
        else:
            sql = "UPDATE wordfreqs SET count = count + ? WHERE category_id = ? AND word = ?"
            values = ( str(count), category_id, word )
            self.word_cache[word][category_id]['count'] += count

        cur.execute( sql, values )
        self.con.commit()

    def removeWord( self, word, count, category_id ):
        ''' remove a word from a category.

            @return bool success
            @param string word
            @param int  count
            @param string category id
        '''
        if word=="":
            return
        oldWord = self.getWord( word, category_id )
        cur = self.get_db_cursor()

        if (0 != oldWord['count'] and 0 >= (oldWord['count']-count)):
            sql = "DELETE FROM wordfreqs WHERE word = ? AND category_id = ?"
            values = ( word, category_id )
            self.word_cache[word][category_id] = {'count': 0}
        else:
            sql = "UPDATE wordfreqs SET count -= ? WHERE category_id = ? AND word = ?"
            values = ( count, category_id, word )
            self.word_cache[word][category_id]['count'] -= count

        cur.execute( sql, values )

    def updateProbabilities( self ):
        ''' update the probabilities of the categories and word count.
        This function must be run after a set of training

            @return bool sucess
        '''
        # first update the word count of each category
        cur = self.get_db_cursor()
        sql = "SELECT category_id, SUM(count) AS total FROM wordfreqs WHERE 1 GROUP BY category_id"
        rs = cur.execute( sql )
        rows = cur.fetchall()
        
        print rows

        total_words = 0

        for row in rows:
            total_words += row['total']

        if (total_words == 0):
            sql = "UPDATE categories SET word_count=0, probability=0 WHERE 1"
            return True

        for row in rows:
            proba = float(row['total']) / float(total_words)
            row_sql = "UPDATE categories SET word_count = ?, probability= ? WHERE category_id = ?"
            row_query = cur.execute( row_sql, (row["total"],proba, row["category_id"]) )
            self.con.commit()

        return True

    def saveReference( self, doc_id, category_id, content):
        ''' save a reference in the database.

            @return bool success
            @param  string reference if, must be unique
            @param  string category id
            @param  string content of the reference
        '''
        sql = "INSERT INTO `references` (id, category_id, content) VALUES (?,?,?)"
        cur = self.get_db_cursor()
        cur.execute( sql, (doc_id,category_id, content) )
        self.con.commit()

    def getReference( self, doc_id):
        ''' get a reference from the database.

            @return array  reference( category_id => ...., content => ....)
            @param  string id
        '''

        cur = self.get_db_cursor()
        sql = "SELECT * FROM `references` WHERE id = ?"
        rs = cur.execute( sql, (doc_id,) )
        if( cur.rowcount==0):
            return {}

        return cur.fetchone()

    def removeReference( self, doc_id):
        ''' remove a reference from the database

            @return bool sucess
            @param  string reference id
        '''
        cur = self.get_db_cursor()
        sql = "DELETE FROM `references` WHERE id = ?"
        rs = cur.execute( sql, (doc_id,) )
        self.con.commit()

    def addcat( self, cat = False, catname = False):
        ''' add a category to the database

            @author Antoine Bajolet [phpdig_at_toiletoine.net]
            @author SPIP [http:#uzine.net/spip/]

            @return bool sucess
            @param  string slug for category
            @param  string name of category
        '''
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

        cur = self.get_db_cursor()
        if self.dbtype=="mysql":
            sql = "INSERT IGNORE INTO categories (category_id, description) VALUES (?,?)"
        else:
            sql = "INSERT OR IGNORE INTO categories (category_id, description) VALUES (?,?)"
        cur.execute( sql, (cat, catname) )

        return True

    def remcat( self, cat = False):
        ''' remove a category to the database

            @author Antoine Bajolet [phpdig_at_toiletoine.net]
            @author SPIP [http:#uzine.net/spip/]

            @return bool sucess
            @param  string slug for category
            @param  string name of category
        '''
        if(not(cat)):
            return False

        cat = re.sub('<[^>]*>', '', cat.strip())
        cat = cat.replace(' ', '')

        if(len(cat)==0):
            return False

        cur = self.get_db_cursor()
        cur.execute("DELETE FROM categories WHERE category_id= ?", (cat,) )
        cur.execute("DELETE FROM `references` WHERE category_id= ?", (cat,) )
        cur.execute("DELETE FROM wordfreqs  WHERE category_id= ?", (cat,) )
        self.updateProbabilities()

        return True

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