# -*- python -*-
# ex: set syntax=python:
from __future__ import print_function

from oauth2client.client import GoogleCredentials
from googleapiclient import discovery


def main():
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)
    project = 'the-pedigree-project'
    zone = 'us-central1-a'

    def get_instance():
        return compute.instances().get(zone=zone, project=project,
                                       instance='buildbot-slave').execute()

    inst = get_instance()
    if inst and inst['status'] == 'RUNNING':
        print('Worker is running, all is OK.')
        return

    # Start the worker.
    print('Starting worker...')
    result = compute.instances().start(zone=zone, project=project,
                                       instance='buildbot-slave').execute()
    if result.get('error'):
        print('Worker failed to start.')
        return

    print('Worker is starting...')


if __name__ == '__main__':
    main()
