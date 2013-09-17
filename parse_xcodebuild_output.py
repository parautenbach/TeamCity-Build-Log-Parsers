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

import re
import sys

# Only change these settings for debugging purposes
# Whether TeamCity style messages must be outputted - default True
__TC_STYLE = True
#__TC_STYLE = False
# Whether all other input must be outputted - default True
__PIPE_ALL = True
#__PIPE_ALL = False

# Regex patterns
__SUITE_START_PATTERN = '^Test Suite \'(.+)\' started at .+$'
__SUITE_START_REGEX = re.compile(__SUITE_START_PATTERN)
__SUITE_STOP_PATTERN = '^Test Suite \'(.+)\' finished at .+$'
__SUITE_STOP_REGEX = re.compile(__SUITE_STOP_PATTERN)
__CASE_START_PATTERN = '^Test Case \'-\[(.+?)\]\' started\.$'
__CASE_START_REGEX = re.compile(__CASE_START_PATTERN)
__CASE_STOP_PATTERN = '^Test Case \'-\[(.+?)\]\' (passed|failed) \((.+?) seconds\)\.$'
__CASE_STOP_REGEX = re.compile(__CASE_STOP_PATTERN)
__CASE_FAIL_PATTERN = '^(.+?):(\d+): error: \-\[(.+?)\] : \'(.+?)\' \[FAILED\], (.+)$'
__CASE_FAIL_REGEX = re.compile(__CASE_FAIL_PATTERN)
__BUILD_STOP_PATTERN = '^\*\* BUILD (FAILED|SUCCEEDED) \*\*$'
__BUILD_STOP_REGEX = re.compile(__BUILD_STOP_PATTERN)
__BUILD_SUCCESS_STATUS = 'SUCCESS'
__BUILD_FAIL_STATUS = 'FAIL'
__BUILD_FAIL_OUTPUT_PATTERN = '^(.+?)\n(.+?)\n(.+)$'
__BUILD_FAIL_OUTPUT_REGEX = re.compile(__BUILD_FAIL_OUTPUT_PATTERN)

# Global flag for build status
__failure = False

def is_suite_start(line):
    return not __SUITE_START_REGEX.search(line) is None

def is_suite_stop(line):
    return not __SUITE_STOP_REGEX.search(line) is None

def is_case_start(line):
    return not __CASE_START_REGEX.search(line) is None

def is_case_stop(line):
    return not __CASE_STOP_REGEX.search(line) is None

def is_build_stop(line):
    return not __BUILD_STOP_REGEX.search(line) is None

def get_suite_start_matches(line):
    return (__SUITE_START_REGEX.match(line).group(1))

def get_suite_stop_matches(line):
    return (__SUITE_STOP_REGEX.match(line).group(1))

def get_case_start_matches(line):
    return (__CASE_START_REGEX.match(line).group(1))

def get_case_stop_matches(line):
    match = __CASE_STOP_REGEX.match(line)
    case_name = match.group(1)
    case_status = match.group(2)
    dur_split = match.group(3).split('.') 
    s = int(dur_split[0])*1000
    ms = int(dur_split[1])
    case_dur = s + ms
    return (case_name, case_status, case_dur)

def is_failure(status):
    if status == 'failed':
        set_build_status(__BUILD_FAIL_STATUS)
        return True
    else:
        return False

def get_build_status():
    global __failure
    if __failure:
        return __BUILD_FAIL_STATUS
    else:
        return __BUILD_SUCCESS_STATUS

def set_build_status(status):
    global __failure
    if status == __BUILD_FAIL_STATUS:
        __failure = True
    else:
        __failure = False

def get_failure_matches(line):
    match = __CASE_FAIL_REGEX.match(line)
    file_ = match.group(1)
    line = match.group(2)
    reason = match.group(5)
    return (file_, line, reason)

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
        print('##teamcity[testFailed name=\'{0}.{1}\' message=\'{1}\' details=\'{2}\']'.format(suite, name, message, details))
    else:        
        print('\t\tMessage: ' + message)
        print('\t\tDetails: '+ details)

def print_build_status_msg(reason):
    failed = (get_build_status() == __BUILD_FAIL_STATUS)
    if __TC_STYLE and failed:
        print('##teamcity[buildStatus status=\'FAILURE\' text=\'{build.status.text}\']')
    elif __TC_STYLE:
        print('##teamcity[buildStatus status=\'SUCCESS\' text=\'{build.status.text}\']')
    elif failed:
        print('Build failed')
        print('Reason:\n{0}'.format(reason.replace('\t', '')))
    else:
        print('Build succeeded')

def main():
    """Parses the output of xcodebuild and generate TeamCity server messages
    for build and test output.
    
    See http://confluence.jetbrains.net/display/TCD4/Build+Script+Interaction+with+TeamCity#BuildScriptInteractionwithTeamCity-ReportingTests
    for more information on TeamCity server messages.
    """
    curr_line = ''
    skip_count = 2
    while not is_build_stop(curr_line):
        prev_line = curr_line
        curr_line = sys.stdin.readline()
        if __PIPE_ALL:
            print(curr_line.strip())
        if is_suite_start(curr_line):
            (suite_name) = get_suite_start_matches(curr_line)
            if skip_count > 0:
                skip_count = skip_count - 1
                continue
            skip_count = skip_count - 1
            print_suite_start_msg(suite_name)
        elif is_suite_stop(curr_line):
            (suite_name) = get_suite_stop_matches(curr_line)
            if skip_count >= 0:
                skip_count = skip_count + 1
                continue
            skip_count = skip_count + 1        
            print_suite_stop_msg(suite_name)
        elif is_case_start(curr_line):
            (case_name) = get_case_start_matches(curr_line)
            print_case_start_msg(suite_name, case_name)
        elif is_case_stop(curr_line):
            (case_name, case_status, duration) = get_case_stop_matches(curr_line)
            if is_failure(case_status):
                (filename, line_number, reason) = get_failure_matches(prev_line)
                print_failure_msg(suite_name, case_name, reason, '{0}:{1}'.format(filename,line_number))
            print_case_stop_msg(suite_name, case_name, case_status, duration)
    build_reason = ''
    ret_code = 0
    if get_build_status() == __BUILD_FAIL_STATUS:
        build_reason = sys.stdin.read().strip()
        ret_code = 1
    print_build_status_msg(build_reason)
    exit(ret_code)

if __name__ == "__main__":
    main()
