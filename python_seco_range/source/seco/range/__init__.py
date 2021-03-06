"""
Library for querying the range webservice - http://github.com/ytoolshed/range
ebourget@linkedin.com
"""
from __future__ import print_function

# Core
try:
    from urllib.parse import quote
except ImportError:
    from urllib2 import quote
import socket
import sys
import getpass

# 3rd party
import requests

__version__ = '2.0'

class RangeException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Range(object):
    def __init__(self, host, user_agent=None, max_char=7500):
        self.host = host
        self.max_char = max_char
        self.headers = {}
        self.headers['User-Agent'] = self.get_user_agent(user_agent)

    def expand(self, expr, ret_list=True):
        if isinstance(expr, list):
                expr = ','.join(expr)

        # If the query is too large for a single query, send it off to
        # split functions
        if len(expr) > self.max_char:
            if ret_list:
                return self.split_query(expr, ret_list)
            else:
                return self.split_collapse(expr)

        if ret_list:
            url = 'http://{}/range/list?{}'.format(self.host, quote(expr))
        else:
            url = 'http://{}/range/expand?{}'.format(self.host, quote(expr))

        try:
            response = requests.get(url, headers=self.headers)
        except requests.exceptions.ConnectionError as e:
            raise RangeException(e)

        if response.status_code != 200:
            raise RangeException("Got {} response code from {}".format(response.status_code, url))
        try:
            exception = response.headers['RangeException']
            raise RangeException(exception)
        except KeyError:
            if ret_list:
                expansion = []
                for line in response.text.splitlines():
                    expansion.append(line.rstrip())
                expansion.sort()
                return expansion
            else:
                return response.text

    def collapse(self, expr):
        '''
        Convenience function for returning collapsed format instead
        of an individual list
        '''
        return self.expand(expr, ret_list=False)

    def split_query(self, expr, ret_list):
        '''
        Range queries are GETs, which have a URL limit of 8190 on
        apache systems.    This method splits up long queries and
        makes multiple calls, merging the result into a list.

        This is, admittedly, a total hack.    Should fix range to accept PUT
        for queries.
        '''
        final_list = []
        new_list = self.build_split_list(expr)
        for short_expr in new_list:
            final_list.append(self.expand(short_expr, ret_list=ret_list))

        return final_list

    def split_collapse(self, expr):
        '''
        Helper function for split collapses, since they may need to split
        and call multiple times to get the final collapsed list
        '''
        prev_expr = ''
        coll_expr = expr
        # Keep collapsing until the list stops changing
        while prev_expr != coll_expr:
            prev_expr = coll_expr
            coll_list = self.split_query(coll_expr, ret_list=False)
            coll_expr = (','.join(coll_list)).strip(',')
        return coll_expr

    def build_split_list(self, expr):
        '''
        Take the max_char function and break up an expression list based on
        the character limits of individual items
        '''
        if isinstance(expr, str):
            expr = expr.split(',')
            expr.sort()
        new_list = []
        running_total = 0
        position = 0
        for range in expr:
            running_total += len(range) + 1
            if running_total > self.max_char:
                running_total = 0
                position += 1
            try:
                new_list[position].append(range)
            except (AttributeError, IndexError):
                new_list.append([range,])

        return new_list

    def get_user_agent(self, provided_agent):
        """
        Build a verbose User-Agent for sending to the range server.
        Terribly useful if you ever have to track down crappy clients.
        """
        myhost = socket.gethostname()
        me = getpass.getuser()
        myscript = provided_agent or sys.argv[0] or 'seco.range'
        return '{0}/{1} ({2}; {3})'.format(myscript, __version__, me, myhost)

if __name__ == '__main__':
    try:
        r = Range("localhost:80")
    except RangeException as e:
        print(e)
        sys.exit(1)
    print(r.expand(sys.argv[1]))
