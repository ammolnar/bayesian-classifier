Naive Bayesian Classification library
=====================================

Produce naive bayesian classifications that can be applied to text strings. The naive bayesian 
classifier produces a model for classifying strings based on the words used in strings that 
have already been Each classification needs to be trained, and the trained data is saved in an 
sqlite database (files ending `.db`). Data to classify can then be run against these sqlite 
databases to determine categories for individual rows.

The classification library is based on [one developed in PHP](https://web.archive.org/web/20111211215027/http://www.xhtml.net/php/PHPNaiveBayesianFilter).

Python requirements
-------------------

### External libraries

-	**[configargparse](https://pypi.python.org/pypi/ConfigArgParse/0.9.1)**
-	**[unicodecsv](https://pypi.python.org/pypi/unicodecsv/0.14.1)**

### Standard libraries

-	**sqlite3** [Lightweight database]
-	**re**
-	**math**
-	**collections**

Training a classifier
---------------------

To run the bayesian classifier, first the model needs to be trained using data that has already 
been classified. This is done through the `bayesian_training.py` script. As well as training a
model from scratch, additional data can also be added to a model.

### Input data

The input data for training a model should consist of a CSV file with at least three columns. The
three needed columns are:

-	**ID column** giving a unique identifier for each row
-	**Description column** giving the text string that will be used to produce the classifier.
-	**Category column** giving the category of the string for that row

Any number of categories can be used, but the classifier works best for a smaller number of categories.

The CSV file can contain any number of other columns, these will be ignored

### How to run

To train the classifier, run something similar to the following command:

	> python bayesian_training.py --database indiv.db --id-column id --desc-column original_name --category-column Company --reset "arts-council.csv"

The most important options are:

-	`--database`: the sqlite database file where the processed training data will be saved.
-	`--id-column`: the name (or zero-based column number) holding a unique ID for the row.
-	`--desc-column`: the name (or number) of the column holding the text to be used as training data.
-	`--category-column`: the name (or number) of the column holding the category.
-	`--reset`: if specified, any existing data in the database will be deleted before training.

The last part of the command is the CSV file that contains the training data.
	
### Data outputs

The training will produce an sqlite3 database with the processed training data included. The file
is saved in the location specified in the `--database` tab. The database consists of three tables:

-	`references`: A copy of the original source data (the id, description and category columns)
-	`wordfreqs`: A list of every word found in the training data alongside the category it was 
	found in and how many times it has been seen in that category.
-	`categories`: A list of the categories used along with the overall probability that a row
	is in that category.
	
This database can then be used by the `bayesian.py` script to classify unclassified data.

### Configuration options

The following options are available for the configuration file. The arguments are parsed using
[configargparse](https://pypi.python.org/pypi/ConfigArgParse/0.9.1) so can also be set by a 
configuration file which is referenced using a `--config` flag.

-	`--config`: a configuration file can be used to specify these options
-	`--database`: the sqlite database file where the processed training data will be saved.
-	`--test`: if set, only 100 rows will be included
-	`--reset`: if specified, any existing data in the database will be deleted before training.
-	`--limit`: if set, only the first X rows will be set
-	`--id-column`: the name (or zero-based column number) holding a unique ID for the row.
-	`--desc-column`: the name (or number) of the column holding the text to be used as training data.
-	`--category-column`: the name (or number) of the column holding the category.
-	`--header`, `--no-header`: whether or not the first row of the CSV file contains column headers
-	`--delimiter`: CSV file delimiter

Running a classifier
--------------------

Once trained, the classifier can then be run on unclassified data, in the form of a CSV file.

### Input data

The input data consists of two parts:

1.	An sqlite database produced using the process above

2.	A CSV file with a column that needs classifying.

### How to run

To run the classifier on an unclassified CSV file, use the following command.

	> python bayesian.py --database indiv.db --column original_name "arts-council-test.csv" "arts-council-test-results.csv"

The following options are the most crucial:

-	`--database`: the database produced from the training data
-	`--column`: the name (or zero-based column number) holding the data to classify

The first file name after the option flags is the input CSV file, and the second file name is
where the output file will be saved.

### Data outputs

The data output is a copy of the original CSV file, with a column added with the best match
for the category for each row. If no match meets the threshold then a null value is added.

A column with the match score (out of 100) is also added.

### Configuration options

-	`--config`: a configuration file can be used to specify these options
-	`--database`: the sqlite database file where the processed training data is held.
-	`--test`: if set, only 100 rows will be included
-	`--limit`: if set, only the first X rows will be classified
-	`--threshold`: the score above which results will be included in the data. The default is 
	-0.1 (includes any result)  
-	`--column`: the name (or zero-based column number) holding the text to be classified.
-	`--result-col`: the name of the column that will hold the result.
-	`--score-col`: the name of the column that will hold the score.
-	`--header`, `--no-header`: whether or not the first row of the CSV file contains column headers
-	`--delimiter`: CSV file delimiter