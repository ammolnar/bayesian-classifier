import MySQLdb as mdb
import sys
import argparse
import utils.mysql_config as msc
import urllib
import urllib2

def main():

    con = mdb.connect( msc.host, msc.user, msc.password, 'almanac')
    parser = argparse.ArgumentParser(description='Check a set of accounts against the part B data to see whether anything has actually been entered.')
    parser.add_argument("-f", "--financial_year", default="2012-13", help='The financial year in format YYYY-YY (default is 2012-13)')
    args = parser.parse_args()
    
    sql = "SELECT s.aKey, a.account_id, COUNT(*) AS `records` FROM almanac.sample s, charityaccounts.accountrecord a, charityaccounts.financerecord f WHERE s.aKey = a.aID AND s.financial_year = %s AND s.aKey = f.aKey GROUP BY s.aKey"

    cur = con.cursor(mdb.cursors.DictCursor)
    cur.execute(sql, args.financial_year)
    result = cur.fetchall()
    
    for account in result:
        data = urllib.urlencode( { "accountid": account["account_id"] } )
        response = urllib2.urlopen('http://almanac/dataAdmin/ajax.show_part_b.php', data )
        rows = response.read()
		if(rows==account["records"]):
			print account["aKey"], account["account_id"], account["records"], rows, "*****"
		else:
			print account["aKey"], account["account_id"], account["records"], rows

if __name__ == '__main__':
    main()
