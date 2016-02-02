from naivebayesian.naivebayesian import NaiveBayesian
import utils.mysql_config as msc
import MySQLdb as mdb
import argparse
import csv
import io

def main():

    # get the arguments we need
    parser = argparse.ArgumentParser(description='Apply bayesian classification to a set of rows.')
    
    parser.add_argument("bayesset", help='The bayesian set used to base training on')
    parser.add_argument("data_input", help='A csv file with rows to be classified')
    parser.add_argument("-db", "--database", default="bayesian", help='The database used to store the bayesian classification data')
    parser.add_argument("-desc", "--desc_column", default=1, help='The column name containing the description we are training on')
    parser.add_argument("--frID", default='frID', help='The column name containing the finance record id')
    parser.add_argument("-cat", "--category_type", default='type_class', help='The class we are training on')
    parser.add_argument('--test', dest='test', action='store_true', help='Whether to do a test run (only 10 rows)')
    parser.add_argument('-l', '--limit', type=int, default=0, help='Put a limit on the number of rows run')
    parser.add_argument('--header', dest='header', action='store_true', help='Whether the CSV file has a header row')
    parser.add_argument('--no-header', dest='header', action='store_false', help='Whether the CSV file has a header row')
    parser.add_argument('--reset', dest='reset', action='store_true', help='Whether to reset the database tables')
    parser.add_argument("-t", "--threshold", type=float, default=-0.01, help='The threshold (out of 100) for accepting a matchs on (default -0.01 ie no threshold)')
    parser.add_argument("-d", "--delimiter", default=",", help='Delimiter used in the CSV file')
    parser.set_defaults(header=True)
    parser.set_defaults(test=False)
    parser.set_defaults(reset=False)
    args = parser.parse_args()
    
    # set up for test
    if args.test:
        args.limit = 10
    
    # stats used to track progress
    rows = 0
    success_trained = 0        # the number of items we've trained with
    
    # set up the bayesian classifiers
    nb = NaiveBayesian( msc.user, msc.password, msc.host, args.database, args.bayesset, args.reset)
    
    # open our file and load as CSV
    with open(args.data_input, 'rb') as csvfile:
        
        if(args.header):
            datarows = csv.DictReader(csvfile, delimiter=args.delimiter)
            # parse the first row of the CSV file to get the fieldnames
        else:
            datarows = csv.reader(csvfile, delimiter=args.delimiter)
            args.desc_column = int(args.desc_column)
        key = 0           
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
        
            # our result
            if to_train:
                to_train = to_train.strip()
                row_result = None
                options = 0
                train_result = nb.train( docid = row[args.frID], category_id = row[args.category_type], content=to_train ) # use the Naive Bayesian filter to train with this record
            if train_result:
                success_trained += 1
            # maintain the loop
            key += 1
            if(args.limit > 0 and key >= args.limit):
                break # if we're testing or limited then break the loop
    print success_trained, "rows used for training"
    nb.updateProbabilities()
                    
                    
if __name__ == '__main__':
    main()