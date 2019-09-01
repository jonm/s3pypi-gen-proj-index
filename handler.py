# Copyright 2019 Jonathan T. Moore
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import os
import re

import boto3
import botocore

def _set_logging():
    lvl = os.environ.get('LOG_LEVEL','INFO')
    names = { 'DEBUG' : logging.DEBUG, 'INFO' : logging.INFO,
              'WARN' : logging.WARN, 'WARNING' : logging.WARNING,
              'ERROR' : logging.ERROR, 'CRITICAL' : logging.CRITICAL,
              'FATAL' : logging.FATAL }
    if lvl not in names:
        logging.warn("unexpected LOG_LEVEL %s" % (lvl,))
        lvl = 'INFO'
    logging.getLogger().setLevel(names[lvl])

def _get_configuration():
    config = {}
    for v in ['INDEX_BUCKET','ARTIFACT_BUCKET','REBUILD_ROOT_TOPIC']:
        config[v] = os.environ[v]
    return config

def _projects_to_rebuild(config, event):
    out = []
    update_events = ['ObjectCreated:Put', 'ObjectCreated:Post',
                     'ObjectCreated:Copy', 'ObjectCreated:*'
                     'ObjectCreated:CompleteMultipartUpload',
                     'ObjectRemoved:*',
                     'ObjectRemoved:Delete',
                     'ObjectRemoved:DeleteMarkerCreated',
                     'ReducedRedundancyLostObject']
                     
    for record in event['Records']:
        if record['eventSource'] == 'aws:s3':
            if record['eventName'] in update_events:
                proj = record['s3']['object']['key'].split("/")[0]
                if proj not in out: out.append(proj)
            elif record['eventSource'] == 'aws:sns':
                inner = json.loads(record['Sns']['Message'])
                for proj in _projects_to_rebuild(config, inner):
                    if proj not in out: out.append(proj)
            else:
                logging.warn("Unexpected record: %s" % (record,))
    return out

def _all_projects(config):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(config['ARTIFACT_BUCKET'])
    out = []
    for obj in bucket.objects.all():
        proj = obj.key.split("/")[0]
        if proj not in out: out.append(proj)
    return out

def _normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()

def _normalize_projects(projects):
    out = {}
    for proj in projects:
        norm = _normalize(proj)
        if norm not in out: out[norm] = []
        if proj not in out[norm]: out[norm].append(proj)
    return out

def _object_exists(bucket, key):
    s3 = boto3.resource('s3')
    try:
        s3.Object(bucket, key).load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            raise
    return True

def _rebuild_project_index(config, project, prefixes):
    rebuild_root = False
    
    # if the per-project index does not exist, this is a new project
    # and we will need to rebuild the root index
    if not _object_exists(config['INDEX_BUCKET'],
                          project + "/index.html"):
        logging.info("New project index for '%s'" % (project,))
        rebuild_root = True

    s3 = boto3.resource('s3')
    src_bucket = s3.Bucket(config['ARTIFACT_BUCKET'])
    
    artifacts = []
    for prefix in prefixes:
        for obj in src_bucket.objects.filter(Prefix=prefix + "/"):
            filename = obj.key.split("/")[-1]
            uri = "https://%s.s3.amazonaws.com/%s" % (config['ARTIFACT_BUCKET'],
                                                      obj.key)
            artifacts.append((filename, uri))

    artifacts.sort()

    if len(artifacts) > 0:
        html = ("<!DOCTYPE html><html><body>" +
                ' '.join(map(lambda p: "<a href=\"%s\">%s</a>" % (p[1], p[0]),
                             artifacts)) +
                "</body></html>")
        proj_idx = s3.Object(config['INDEX_BUCKET'], project + "/index.html")
        proj_idx.put(Body=html,ContentType="text/html")
        logging.info("Regenerated index for project '%s'" % (project,))
    else:
        logging.info("No artifacts remaining for '%s'" % (project,))
        s3.Object(config['INDEX_BUCKET'], project + "/index.html").delete()
        rebuild_root = True
    
    return rebuild_root


def handle(event, context):
    # cf. https://www.python.org/dev/peps/pep-0503/
    _set_logging()
    config = _get_configuration()

    try:
        projects = _projects_to_rebuild(config, event)
    except:
        logging.warn("Failed to process event: %s" % (event,), exc_info=True)
        projects = _all_projects(config)

    normalized_projects = _normalize_projects(projects)
    rebuild_root = False
    for proj in normalized_projects.keys():
        if _rebuild_project_index(config, proj, normalized_projects[proj]):
            rebuild_root = True

    if rebuild_root:
        logging.info("Triggering rebuild of root index")
        sns = boto3.resource('sns')
        topic = sns.Topic(config['REBUILD_ROOT_TOPIC'])
        topic.publish(Message="{rebuild_root:true}")


