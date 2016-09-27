from naivebayesian.naivebayesian import NaiveBayesian
import configargparse
import unicodecsv as csv
import io

def main():

    # get the arguments we need
    parser = configargparse.ArgumentParser(description='Apply bayesian classification to a set of rows.',
        default_config_files=['config.cfg'],
        ignore_unknown_config_file_keys=True)
    
    # key files
    parser.add_argument("input", help='A csv file with rows to be classified')
    parser.add_argument("output", help='The name of a file to write to')
    parser.add_argument("-c", "--config", default=None, is_config_file=True, help='Address of a config file')
    
    # database variables
    parser.add_argument("-db", "--database", default="bayesian", help='The database used to store the bayesian classification data. For sqlite this will be used as the database file.')
    parser.add_argument('--sqlite', dest='sqlite', action='store_true', help='Whether to use SQlite to store the data')
    parser.add_argument('--mysql', dest='sqlite', action='store_false', help='User a MySQL database')
    
    # configuration variables
    parser.add_argument('--test', dest='test', action='store_true', help='Whether to do a test run (only 10 rows)')
    parser.add_argument('-l', '--limit', type=int, default=0, help='Put a limit on the number of rows run')
    parser.add_argument("-t", "--threshold", type=float, default=-0.01, help='The threshold (out of 100) for accepting a match on (default -0.01 ie no threshold)')
    
    # CSV file options
    parser.add_argument("--column", default=0, help='The column name or number of the content to be classified')
    parser.add_argument('--header', dest='header', action='store_true', help='Whether the CSV file has a header row')
    parser.add_argument('--no-header', dest='header', action='store_false', help='Whether the CSV file has a header row')
    parser.add_argument('--result-col', default='result', help='Header used for the results column')
    parser.add_argument('--score-col', default='score', help='Header used for the result score column')
    parser.add_argument("-d", "--delimiter", default=",", help='Delimiter used in the CSV file')
    parser.set_defaults( header=True, test=False, sqlite=True )
    
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
    nb = NaiveBayesian( args.database )
    
    # open our file and load as CSV
    with open(args.input, 'rb') as csvfile:
        
        if(args.header):
            datarows = csv.DictReader(csvfile, delimiter=args.delimiter)
        else:
            datarows = csv.reader(csvfile, delimiter=args.delimiter)
            args.column = int(args.column)
        key = 0
        
        nb.updateProbabilities()
        
        with open(args.output, 'w') as csvoutput:
            headers = datarows.fieldnames
            headers.append(args.result_col)
            headers.append(args.score_col)
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
                    
                row_result_category = None
                row_result_score = None
            
                # our result
                if to_cat:
                    row_result = nb.bestMatch( to_cat, args.threshold )
                    if row_result:
                        classified += 1
                        row_result_category = row_result[0]
                        row_result_score = row_result[1]
                    else:
                        not_classified += 1
                    attempted_rows += 1
                    #writer.writerow( row ) # this will write out the FrID and description and an extra column called 'result' but with nothing in
                    if key % 100 == 0:
						print key
						
                
                row[args.result_col] = row_result_category
                row[args.score_col] = row_result_score
                writer.writerow( row ) # this row will write out the category as well as the FrID and description if 'row[args.score_col] = row_result_score' is commented out - they cannot be used together
                
                if args.test:
                    print row
                
                # maintain the loop
                key += 1
                if(args.limit > 0 and key >= args.limit): 
                    break # if we're testing or limited then break the loop

    print attempted_rows, "rows attempted"
    print classified, "rows classified"
    print not_classified, "rows not classified"
                    
                    
if __name__ == '__main__':
    main()