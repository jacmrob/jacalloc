FROM jacmrob/jacalloc

# The jacalloc image is so outdated at this point that installing dependencies no longer works.
# We'll be replacing jacalloc with Sherlock soon, so this Dockerfile simply patches
# the existing Docker image with our local updates to jacalloc's files.

# (see Dockerfile.original for the original Dockerfile)

COPY app /app
