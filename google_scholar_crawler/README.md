# Google Scholar citation updater

The workflow uses SerpApi as its primary Google Scholar data source because
Google commonly blocks direct requests from GitHub Actions IP addresses.

Configure these repository secrets under **Settings → Secrets and variables →
Actions**:

- `GOOGLE_SCHOLAR_ID`: the value after `user=` in the public Scholar profile URL.
- `SERPAPI_KEY`: an API key from a SerpApi account.

After pushing the workflow, run **Actions → Get Citation Data → Run workflow**.
The generated `gs_data.json` and `gs_data_shieldsio.json` files are published to
the `google-scholar-stats` branch. If `SERPAPI_KEY` is absent or the request
fails, the updater tries `scholarly` directly and then with free proxies, but
those fallback modes can be blocked by Google.
