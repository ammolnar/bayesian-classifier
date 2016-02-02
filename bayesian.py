from naivebayesian.naivebayesian import NaiveBayesian
import utils.mysql_config as msc
import MySQLdb as mdb
import argparse
import csv
import io

def main():

    # get the arguments we need
    parser = argparse.ArgumentParser(description='Apply bayesian classification to a set of rows.')
    
    parser.add_argument("bayesset", help='The bayesian set used to base classifications on')
    parser.add_argument("input", help='A csv file with rows to be classified')
    parser.add_argument("output", help='The name of a file to write to')
    parser.add_argument("-db", "--database", default="bayesian", help='The database used to store the bayesian classification data')
    parser.add_argument("-c", "--column", default=0, help='The column name or number of the content to be classified')
    parser.add_argument('--test', dest='test', action='store_true', help='Whether to do a test run (only 10 rows)')
    parser.add_argument('-l', '--limit', type=int, default=0, help='Put a limit on the number of rows run')
    parser.add_argument('--header', dest='header', action='store_true', help='Whether the CSV file has a header row')
    parser.add_argument('--no-header', dest='header', action='store_false', help='Whether the CSV file has a header row')
    parser.add_argument("-t", "--threshold", type=float, default=-0.01, help='The threshold (out of 100) for accepting a match on (default -0.01 ie no threshold)')
    parser.add_argument("-d", "--delimiter", default=",", help='Delimiter used in the CSV file')
    parser.set_defaults(header=True)
    parser.set_defaults(test=False)
    
    args = parser.parse_args()
    
    # set up for test
    if args.test:
        args.limit = 10
        
    # set up the output if none given
    if( args.output is None):
        args.output = io.StringIO()
    
    # stats used to track progress
    rows = 0
    attempted_rows = 0    # the number of rows that have been attempted
    classified = 0        # the number of items we've classified
    not_classified = 0    # the number of items that haven't been classified
    
    # set up the bayesian classifiers
    nb = NaiveBayesian( msc.user, msc.password, msc.host, args.database, args.bayesset)
    
    # open our file and load as CSV
    with open(args.input, 'rb') as csvfile:
        
        if(args.header):
            datarows = csv.DictReader(csvfile, delimiter=args.delimiter)
        else:
            datarows = csv.reader(csvfile, delimiter=args.delimiter)
            args.column = int(args.column)
        key = 0
        
        with open(args.output, 'w') as csvoutput:
            headers = datarows.fieldnames
            headers.append('result')
            writer  = csv.DictWriter(csvoutput, fieldnames=headers, lineterminator='\n', delimiter=args.delimiter)
            writer.writeheader()
            
            # go through each row
            for row in datarows:
            
                # check if we're doing a header row
                if(args.header==False):
                    new_row = {}
                    for k, v in enumerate(row):
                        new_row[k] = v
                    row = new_row
            
                # get the item we're categorising
                to_cat = None
                if(args.header == False or args.column in row):
                    to_cat = row[args.column]
            
                # our result
                if to_cat:
                    row_result = nb.bestMatch( to_cat )
                    if row_result:
                        classified += 1
                    else:
                        not_classified += 1
                    attempted_rows += 1
                    row["result"] = row_result
                    writer.writerow( row )
                    if key % 100 == 0:
                        print key
                
                # maintain the loop
                key += 1
                if(args.limit > 0 and key >= args.limit):
                    break # if we're testing or limited then break the loop

    print attempted_rows, "rows attempted"
    print classified, "rows classified"
    print not_classified, "rows not classified"
                    
                    
if __name__ == '__main__':
    main()