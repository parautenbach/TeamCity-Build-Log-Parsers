#!/usr/bin/python
# Copyright 2013 Pieter Rautenbach
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Usage:
# <your_command> 2>&1 | /usr/local/whatsthatlight/build_runners/parse_android_testrunner_output.py

# Imports
import re
import sys
import datetime

# Only change these settings for debugging purposes
# Whether TeamCity style messages must be outputted - default True
__TC_STYLE = True
#__TC_STYLE = False
# Whether all other input must be outputted - default True
__PIPE_ALL = True
#__PIPE_ALL = False

# Patterns
__CASE_START_PATTERN = '^(.+?) I/TestRunner.+? started: (.+?)\((.+?)\)$'
__CASE_START_REGEX = re.compile(__CASE_START_PATTERN)
__CASE_STATUS_PATTERN = '^(.+?) I/TestRunner.+? (passed|failed): (.+?)\((.+?)\)$'
__CASE_STATUS_REGEX = re.compile(__CASE_STATUS_PATTERN)
__CASE_STOP_PATTERN = '^(.+?) I/TestRunner.+? finished: (.+?)\((.+?)\)$'
__CASE_STOP_REGEX = re.compile(__CASE_STOP_PATTERN)
__DATETIME_PATTERN = '^([0-9]+)-([0-9]+) ([0-9]+):([0-9]+):([0-9]+).([0-9]+)$'
__DATETIME_REGEX = re.compile(__DATETIME_PATTERN)
__BUILD_FAIL_STATUS = 'failed'
__ASSERTION_FAILED_PATTERN = '^.+?: (junit.framework.AssertionFailedError: expected:(.+?) but was:(.+))$'
__ASSERTION_FAILED_REGEX = re.compile(__ASSERTION_FAILED_PATTERN)
__FAILED_LINE_OF_CODE_PATTERN = '^.+?at {0}\.{1}\((.+?):([0-9]+)\)$'

# Global flag for build status
__failure = False

# Auxiliary methods/functions

def is_case_start(line):
    return not __CASE_START_REGEX.search(line) is None

def is_case_stop(line):
    return not __CASE_STOP_REGEX.search(line) is None

def is_case_status(line):
    return not __CASE_STATUS_REGEX.search(line) is None

def is_assertion_failed(line):
    return not __ASSERTION_FAILED_REGEX.search(line) is None

def get_assertion_failed_matches(line):
    match = __ASSERTION_FAILED_REGEX.match(line)
    reason = match.group(1)
    expected = match.group(2)
    actual = match.group(3)
    return (reason, expected, actual)

def get_case_start_matches(line):
    match = __CASE_START_REGEX.match(line)
    test_start_time = match.group(1)
    test_name = match.group(2)
    test_suite = match.group(3)
    return (test_suite, test_name, test_start_time)

def get_case_status_matches(line):
    match = __CASE_STATUS_REGEX.match(line)
    test_stop_time = match.group(1)
    test_status = match.group(2)
    test_name = match.group(3)
    test_suite = match.group(4)
    return (test_suite, test_name, test_stop_time, test_status)

def is_failure(status):
    if status == __BUILD_FAIL_STATUS:
        set_build_status(__BUILD_FAIL_STATUS)
        return True
    else:
        return False

def is_failed_line_of_code(line, test_suite, test_name):
    pattern = re.compile(__FAILED_LINE_OF_CODE_PATTERN.format(test_suite, test_name))
    return not pattern.search(line) is None

def get_failed_line_of_code(line, test_suite, test_name):
    pattern = re.compile(__FAILED_LINE_OF_CODE_PATTERN.format(test_suite, test_name))
    match = pattern.match(line)
    filename = match.group(1)
    line_number = match.group(2)
    return (filename, line_number)

def get_build_failed_status():
    global __failure
    return __failure

def set_build_status(failed):
    global __failure
    __failure = failed

def get_failure_matches(line):
    match = __CASE_FAIL_REGEX.match(line)
    file_ = match.group(1)
    line = match.group(2)
    reason = match.group(5)
    return (file_, line, reason)

def parse_datetime(time_str):
    match = __DATETIME_REGEX.match(time_str)
    year = datetime.date.today().year
    month = int(match.group(1))
    day = int(match.group(2))
    hour = int(match.group(3))
    minute = int(match.group(4))
    second = int(match.group(5))
    microsec = int(match.group(6))
    return datetime.datetime(year, month, day, hour, minute, second, microsec * 1000)

def calculate_duration(test_start_time, test_stop_time):
    start_datetime = parse_datetime(test_start_time)
    stop_datetime = parse_datetime(test_stop_time)
    duration = stop_datetime - start_datetime
    return int(duration.seconds * 1000.0 + duration.microseconds / 1000.0)

# TeamCity Server Messages
def print_suite_start_msg(name):
    if __TC_STYLE:
        print('##teamcity[testSuiteStarted name=\'{0}\']'.format(name))
    else:
        print('Suite start: {0}'.format(name))

def print_suite_stop_msg(name):
    if __TC_STYLE:
        print('##teamcity[testSuiteFinished name=\'{0}\']'.format(name))
    else:
        print('Suite stop: {0}'.format(name))

def print_case_start_msg(suite, name):
    if __TC_STYLE:
        print('##teamcity[testStarted name=\'{0}.{1}\' captureStandardOutput=\'true\']'.format(suite, name))
    else:
        print('\tCase start: {0}'.format(name))

def print_case_stop_msg(suite, name, status, duration):
    if __TC_STYLE:
        print('##teamcity[testFinished name=\'{0}.{1}\' duration=\'{2}\']'.format(suite, name, duration))
    else:
        print('\t\tCase status: {0}'.format(status))
        print('\t\tCase duration: {0}ms'.format(duration))
        print('\tCase stop: {0}'.format(name))

def print_failure_msg(suite, name, message, details):
    if __TC_STYLE:
        print('##teamcity[testFailed name=\'{0}.{1}\' message=\'{2}\' details=\'{3}\']'.format(suite, name, message, details))
    else:
        print('\t\tMessage: ' + message)
        print('\t\tDetails: '+ details)

def print_build_status_msg(reason):
    failed = get_build_failed_status()
    if __TC_STYLE and failed:
        print('##teamcity[buildStatus status=\'FAILURE\' text=\'{build.status.text}\']')
    elif __TC_STYLE:
        print('##teamcity[buildStatus status=\'SUCCESS\' text=\'{build.status.text}\']')
    elif failed:
        print('Build failed')
        print('Reason:\n{0}'.format(reason.replace('\t', '')))
    else:
        print('Build succeeded')

# Main
def main():
    """Parses the output of the Android Test Runner and generate TeamCity server messages
    for build and test output.

    See http://confluence.jetbrains.net/display/TCD4/Build+Script+Interaction+with+TeamCity#BuildScriptInteractionwithTeamCity-ReportingTests
    for more information on TeamCity server messages.
    """

    # TC expects build messages in the order start, optional failure message, 
    # stop/finished message. However, the log we get gives a pass in the order
    # start-finish-pass and a failure in the order start-failure-finish. This
    # poses a problem in order to output the TC messages in the required
    # order. To achieve that, we cannot terminate when we get a finish message,
    # because if it would've been a pass, we're not there yet in the log 
    # (the finish message precedes the pass message). If it's a failure, the
    # order is correct though. To work around this, we keep state of the 
    # current test's status. 

    failed_cnt = 0
    prev_test_suite = ''
    for line in sys.stdin:
        line = line.strip()
        if __PIPE_ALL:
            print(line)
        if is_case_start(line):
            this_test_failed = False
            (test_suite, test_name, test_start_time) = get_case_start_matches(line)
            if not test_suite == prev_test_suite:
                if not prev_test_suite == '':
                    print_suite_stop_msg(prev_test_suite)
                print_suite_start_msg(test_suite)
                prev_test_suite = test_suite
            print_case_start_msg(test_suite, test_name)
        elif is_case_status(line):
            (test_suite, test_name, test_stop_time, test_status) = get_case_status_matches(line)
            duration = calculate_duration(test_start_time, test_stop_time)
            if test_status == __BUILD_FAIL_STATUS:
                this_test_failed = True
                set_build_status(True)
                failed_cnt = failed_cnt + 1
            if not this_test_failed:
                print_case_stop_msg(test_suite, test_name, test_status, duration)
        elif is_case_stop(line) and this_test_failed:
            print_case_stop_msg(test_suite, test_name, test_status, duration)
        elif is_assertion_failed(line):            
            (reason, expected, actual) = get_assertion_failed_matches(line)
        elif is_failed_line_of_code(line, test_suite, test_name):
            (filename, line_number) = get_failed_line_of_code(line, test_suite, test_name)
            print_failure_msg(test_suite, test_name, reason, '{0}:{1}'.format(filename, line_number))
    print_suite_stop_msg(test_suite)
    build_reason = ''
    ret_code = 0
    if get_build_failed_status():
        build_reason = '{0} test(s) failed'.format(failed_cnt)
        ret_code = 1
    print_build_status_msg(build_reason)
    exit(ret_code)

if __name__ == "__main__":
    main()
