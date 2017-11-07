# Everywhere Bible API

This generates the static files for the Everywhere Bible API. This is currently
only used for public domain Bibles, and currently only supports KJV.

## Usage

Run something like:

    python -m everywherebible ../some/directory/public/api/kjv/v1

For a full description, run:

    python -m everywherebible -h

## Deploying

Push to the master branch of this repository to deploy. This generates the
files to the `gh-pages` branch, which is fronted by Cloudflare.

## Testing

    python -m unittest discover

## Credits

The source for the KJV Bible comes from [ebible.org](http://ebible.org). Thank
you so much for your work!
