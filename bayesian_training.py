from naivebayesian.naivebayesian import NaiveBayesian
import configargparse
import unicodecsv as csv
import io

def main():

    # get the arguments we need
    parser = configargparse.ArgumentParser(description='Train a bayesian filter on a set of data.',
        default_config_files=['config.cfg'],
        ignore_unknown_config_file_keys=True)
    
    # key files
    parser.add_argument("data_input", help='A csv file with rows to be classified')
    parser.add_argument("-c", "--config", default=None, is_config_file=True, help='Address of a config file')
    
    # database variables
    parser.add_argument("-db", "--database", default="bayesian.db", help='The database used to store the bayesian classification data. For sqlite this will be used as the database file.')
    parser.add_argument('--sqlite', dest='sqlite', action='store_true', help='Whether to use SQlite to store the data')
    parser.add_argument('--mysql', dest='sqlite', action='store_false', help='User a MySQL database')
    
    # configuration variables
    parser.add_argument('--test', dest='test', action='store_true', help='Whether to do a test run (only 10 rows)')
    parser.add_argument('--reset', dest='reset', action='store_true', help='Whether to reset the database before it\'s run')
    parser.add_argument('-l', '--limit', type=int, default=0, help='Put a limit on the number of rows run')
    parser.add_argument("-t", "--threshold", type=float, default=-0.01, help='The threshold (out of 100) for accepting a match on (default -0.01 ie no threshold)')
    
    # CSV file options
    parser.add_argument("-desc", "--desc-column", default=1, help='The column name containing the description we are training on')
    parser.add_argument("-id", "--id-column", default='id', help='The column name containing the unique record id')
    parser.add_argument("-cat", "--category-column", default='class', help='The column containing data we are training on')
    parser.add_argument('--header', dest='header', action='store_true', help='Whether the CSV file has a header row')
    parser.add_argument('--no-header', dest='header', action='store_false', help='Whether the CSV file has a header row')
    parser.add_argument("-d", "--delimiter", default=",", help='Delimiter used in the CSV file')
    parser.set_defaults( header=True, test=False, reset=False, sqlite=True )
    
    args = parser.parse_args()
    
    # set up for test
    if args.test:
        args.limit = 10
    
    # stats used to track progress
    rows = 0
    success_trained = 0        # the number of items we've trained with
    
    # set up the bayesian classifiers
    nb = NaiveBayesian( args.database, reset=args.reset )
    
    # open our file and load as CSV
    with open(args.data_input, 'rb') as csvfile:
        
        if(args.header):
            datarows = csv.DictReader(csvfile, delimiter=args.delimiter, encoding='utf-8')
            # parse the first row of the CSV file to get the fieldnames
        else:
            datarows = csv.reader(csvfile, delimiter=args.delimiter, encoding='utf-8')
            args.desc_column = int(args.desc_column)
        key = 0
        
        print "Starting training", args.data_input
        
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
            if(args.header == False or args.desc_column in row):
                to_train = row[args.desc_column]
                
            # if we're testing then print the row
            if args.test:
                print row
        
            # our result
            if to_train:
                to_train = to_train.strip()
                row_result = None
                options = 0
                # use the Naive Bayesian filter to train with this record
                train_result = nb.train( docid = row[args.id_column], 
                                         category_id = row[args.category_column], 
                                         content=to_train ) 
            if train_result:
                success_trained += 1
                print '\r', success_trained, " rows trained",
                
            # maintain the loop
            key += 1
            if(args.limit > 0 and key >= args.limit):
                break # if we're testing or limited then break the loop
                
    print             
    print success_trained, "rows used for training"
    nb.updateProbabilities()
                    
                    
if __name__ == '__main__':
    main()