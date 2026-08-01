# PUP repository service

This App Engine service hosts the PUP package catalog, package blobs,
dependency graphs, and the current PUP wheel. The HTML and static assets remain
the original site; only the Python runtime and application plumbing have been
updated.

## Test

Install the runtime dependencies and run the focused tests from this directory:

```sh
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests
```

## Deploy

Authenticate `gcloud`. For the first Python 3 deployment, ensure the App Engine
and Cloud Build APIs are enabled:

```sh
gcloud services enable \
  appengine.googleapis.com \
  cloudbuild.googleapis.com \
  --project=the-pedigree-project
```

This legacy project also needs its default App Engine service account granted
access to the deployment staging bucket:

```sh
gcloud storage buckets add-iam-policy-binding \
  gs://staging.the-pedigree-project.appspot.com \
  --member=serviceAccount:the-pedigree-project@appspot.gserviceaccount.com \
  --role=roles/storage.admin
```

Deploy a version without moving production traffic:

```sh
gcloud app deploy app.yaml \
  --project=the-pedigree-project \
  --version=pup-http-python3 \
  --no-promote
```

Smoke-test the version-specific App Engine hostname before migrating traffic.
The service continues to use the existing Datastore kinds and Blobstore data.
