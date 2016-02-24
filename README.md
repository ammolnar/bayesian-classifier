Naive Bayesian Classification library
=====================================

Produce naive bayesian classifications that can be applied to text strings. Each classification
needs to be trained, and the trained data is saved in an sqlite database (files ending `.db`). 
Data to classify can then be run against these sqlite databases to determine categories for 
individual rows.


Python requirements
-------------------

### External libraries

-	configargparse
-	unicodecsv

### Standard libraries

-	**sqlite3** [Lightweight database]
-	**re**
-	**math**
-	**collections**


Training a classifier
---------------------

### Configuration options


### Input data


### How to run

	> python bayesian_training.py --database indiv.db --id-column id --desc-column original_name --category-column Company --reset "arts-council.csv"


### Data outputs


Running a classifier
--------------------

### Configuration options


### Input data

### How to run

	> python bayesian.py --database indiv.db --column original_name --reset "arts-council-test.csv"

### Data outputs
