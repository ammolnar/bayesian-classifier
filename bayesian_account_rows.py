from naivebayesian.naivebayesian import NaiveBayesian
import utils.mysql_config as msc
import MySQLdb as mdb
import argparse
import getpass

def main():

    # get the arguments we need
    parser = argparse.ArgumentParser(description='Apply bayesian classification to a set of rows.')
    
    parser.add_argument("type", choices=["I", "E", "A", "F", "O", "N"], help='The type of rows to classify')
    parser.add_argument("-db", "--database", default="bayesian", help='The database used to store the bayesian classification data')
    parser.add_argument("-s", "--set", dest="bayesset", help='The bayesian set used to base classifications on')
    parser.add_argument("-t", "--threshold", type=float, default=-0.01, help='The threshold (out of 100) for accepting a matchs on (default -0.01 ie no threshold)')
    parser.add_argument("-l", "--limit", type=int, default=10000, help='Limit for the SQL query (default 10000)')
    parser.add_argument("-o", "--offset", type=int, default=0, help='The offset for the SQL query (default 0)')
    parser.add_argument("-m", "--method", default="Bayesian", help='The name given to the method used (default "Bayesian")')
    parser.add_argument("-p", "--priority", type=int, default=1, help='The priority given to the method used (default 1)')
    parser.add_argument("-u", "--user", default=None, help='The name of the user running the procedure')
    
    args = parser.parse_args()
    
    # get the user (if not supplied as a variable)
    if( args.user == None ):
        args.user = getpass.getuser()
    
    # stats used to track progress
    rows = 0
    attempted_rows = 0    # the number of rows that have been attempted
    classified = 0        # the number of items we've classified
    not_classified = 0    # the number of items that haven't been classified
    
    # database sets that can be used
    sets = {
        "I": "type_i_manual",
        "E": "e_type_manual",
        "A": "type_a",
        "F": "type_f",
        "O": "type_o",
        "N": "type_n"
    }
    
    # work out the database tables used (the "set")
    if( args.bayesset == None ):
        args.bayesset = sets[args.type]
    
    # set up the bayesian classifiers
    nb = NaiveBayesian( msc.user, msc.password, msc.host, args.database, args.bayesset)
    nb_source = None
    if(args.type=="I"):
        nb_source = NaiveBayesian( msc.user, msc.password, msc.host, args.database, 'i_source_manual')

    # set up the database and 2 cursors
    con = mdb.connect( msc.host, msc.user, msc.password, 'charityaccounts')
    cur = con.cursor(mdb.cursors.DictCursor)
    cur2 = con.cursor(mdb.cursors.DictCursor)

    # The SQL query that fetches the rows we're looking for from the database.
    # excludes any rows that have already been checked
    entry_sql = """SELECT `financerecord`.*, 
            `_financerecord_flip`.`description` AS `full_desc` 
        FROM `financerecord` 
                LEFT OUTER JOIN `_bayesian_matched` ON `financerecord`.`frID` = `_bayesian_matched`.`frID`,
            `_financerecord_flip`
        WHERE `type` LIKE %s 
            AND `_bayesian_matched`.`frID` IS NULL
            AND `financerecord`.`frID` = `_financerecord_flip`.`frID`
        ORDER BY `record_id` ASC 
        LIMIT %s, %s"""
    
    # get the rows
    source_rows = cur.execute( entry_sql, (args.type + '%', args.offset, args.limit) )
    attempted_rows = cur.rowcount
    
    # the template for the SQL query which will update the classification table
    replace_sql = "REPLACE INTO `_classification` (`frID`, `classification_method`, `type_class`, `source_class`, `priority`, `user`) VALUES ( %s, %s, %s, %s, %s, %s )"
    replace_sql_array = []

    # the template for the SQL query that says a match was attempted
    match_sql = "REPLACE INTO `_bayesian_matched` (`frID`) VALUES ( %s )"
    match_sql_array = []
    
    # go through each row
    for i in range(cur.rowcount):
        source_row = cur.fetchone()
        rows += 1
        
        scores = nb.categorize( source_row["full_desc"] ) # use the Naive Bayesian filter to classify the full description of the financerecord
        options = 0
        type_class = source_class = None
        
        # go through each of the possible scores
        for cat in scores:
            score = scores[cat]
            
            # if the score is positive, and the first one, then let's use it
            # the --threshold could be adjusted to give a higher threshold for chosing the answer (at the moment there is no barrier)
            if( score >= args.threshold and options==0 ):
                type_class = cat
                options += 1
        
        # if we're doing the source too then go through the same procedure
        if( nb_source ):
            scores = nb_source.categorize( source_row["full_desc"] )
            options = 0
            for cat in scores:
                score = scores[cat]
                if( score >= args.threshold and options==0 ):
                    source_class = cat
                    options += 1
        
        # if a type category has been created then lets create the sql statement for this row for 
        # inserting into the _classification table
        if( type_class!= None or source_class!= None ):
            replace_sql_array.append( ( source_row["frID"], args.method, type_class, source_class, args.priority, args.user ) )
            print i, source_row["frID"], source_row["description"], type_class, source_class
            classified += 1        # increment the number of accounts classified
        else:
            print source_row["frID"], source_row["description"], "NOT CLASSIFIED"
            not_classified += 1    # increment the number of non-classified accounts
        
        match_sql_array.append( ( source_row["frID"] ) )
        
        # if we've reached 100 rows then execute the query
        if( len( replace_sql_array ) == 100 ):
            cur2.executemany( replace_sql, replace_sql_array )
            replace_sql_array = []
        
        # if we've reached 1000 rows then execute the query
        if( len( match_sql_array ) == 1000 ):
            cur2.executemany( match_sql, match_sql_array )
            match_sql_array = []
    
    
    # finally if we've got any results left to add them
    if( len( replace_sql_array ) > 0):
        cur2.executemany( replace_sql, replace_sql_array )
    
    # if we've got any no matches left then also add them
    if( len( match_sql_array ) > 0):
        cur2.executemany( match_sql, match_sql_array )
    
    # print the final results
    print attempted_rows, "records attempted from type", args.type, "offset (", args.offset, ")"
    print classified, "records classified"
    print not_classified, "records not classified"
    if(attempted_rows > 0):
        print "Success rate of", (classified / attempted_rows) * 100, "%"
        
    # check how many rows are still remaining
    matches_left_sql = """SELECT `financerecord`.`frID`
        FROM `financerecord` LEFT OUTER JOIN `_bayesian_matched` ON `financerecord`.`frID` = `_bayesian_matched`.`frID`
        WHERE `type` LIKE %s 
            AND `_bayesian_matched`.`frID` IS NULL"""
    cur.execute( matches_left_sql, ( args.type + '%',) )
    print cur.rowcount, "records left to classify from type", args.type


if __name__ == '__main__':
    main()