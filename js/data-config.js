/**
 * Data Source Configuration
 *
 * repoOwner / repoName point at the GitHub account and repository that hosts the
 * `data` branch. Set these to YOUR fork before deploying (e.g. 'Hui7545').
 * The data branch holds the paper JSONL files that this page fetches.
 */

const DATA_CONFIG = {
    /**
     * GitHub repository owner (username)
     * CHANGE THIS to your own GitHub username before deploying.
     */
    repoOwner: 'Hui7545',

    /**
     * GitHub repository name
     */
    repoName: 'daily-arXiv-ai-enhanced',

    /**
     * Data branch name
     * Default: 'data'
     */
    dataBranch: 'data',

    /**
     * Get the base URL for raw GitHub content from data branch
     * @returns {string} Base URL for raw GitHub content
     */
    getDataBaseUrl: function() {
        return `https://raw.githubusercontent.com/${this.repoOwner}/${this.repoName}/${this.dataBranch}`;
    },

    /**
     * Get the full URL for a data file
     * @param {string} filePath - Relative path to the data file (e.g., 'data/2025-01-01.jsonl')
     * @returns {string} Full URL to the data file
     */
    getDataUrl: function(filePath) {
        return `${this.getDataBaseUrl()}/${filePath}`;
    }
};

