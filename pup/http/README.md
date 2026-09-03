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

The package upload callback accepts an optional `dependencies` form field
containing a JSON array of package names. Dependencies are stored on `Package`
entities and emitted in each `packages.pupdb` record. Existing entities need no
Datastore migration: records without the property are served with an empty
dependency list. Newly published versions carry dependency metadata; immutable
historical versions remain unchanged.

Deploy the service before using the dependency-aware uploader. The uploader can
check `/capabilities.json` for `package_dependencies: 1` before sending any
package bytes. Existing uploaders remain compatible because omitting the field
means no dependencies for a new package and preserves metadata on an
idempotent retry of an existing package.

Published package versions are immutable. Re-uploading the same SHA-1 and
dependency list is an idempotent success; attempting to change either for an
existing name, version, and architecture returns HTTP 409 and retains the
original blob. Publish corrected content under a new version.

Accepted uploads keep Blobstore as the repository source and mirror package
bytes to the bucket named by `PUP_PACKAGE_BUCKET` before publishing a new
Datastore record. The mirror streams through a private staging name while
checking the package SHA-1, then copies to the root-level package filename with
create-only generation preconditions. The final object is
`application/octet-stream` with a one-year immutable cache policy. An
idempotent upload also repairs a missing mirror for an existing catalog record.
If mirroring fails, the callback returns an error and does not publish a new
catalog record.

The App Engine service account needs object create and read access in the
package bucket. Limit its object delete access to `.pup-incoming/`, which is the
only prefix the service cleans up. Configure a short lifecycle rule for that
prefix as a final guard if a request is interrupted after staging but before
normal deletion. Final package objects are never overwritten or deleted by the
service.

Catalog selection understands both current dotted versions and historical
suffix forms. SQLite's old compact source versions are compared as grouped
components, so `3090200` is treated as `3.9.2.0` rather than as version
3,090,200.
