# UFO Trust System

## Overview

The UFO Trust System is an experimental, decentralized reputation system for Twitter/X users, primarily focused on the Ufology / UAP (Unidentified Aerial Phenomena) community. It allows users to assign trust or distrust to others based on their perceived credibility, insights, or contributions to the discussion. This system aims to identify influential and trusted voices within the community using an eigenvector-based trust metric, similar to Google's PageRank.

## How It Works

1.  **Trust Assignment via Tweets:**
    *   Users assign trust scores to other Twitter/X users by posting a tweet with a specific format: `#ufotrust @username <score>`
    *   **Score Scale:** Scores range from **0 to 100**.
        *   **0:** Maximum distrust
        *   **50:** Neutral
        *   **100:** Maximum trust
    *   Scores above 50 indicate varying degrees of trust, while scores below 50 indicate varying degrees of distrust.

2.  **Data Collection:**
    *   Automated scripts periodically search Twitter/X for tweets containing the `#ufotrust` hashtag and valid trust commands.

3.  **Score Calculation:**
    *   The collected trust assignments are processed to build a trust network.
    *   Users' input scores (0-100) are internally mapped to a normalized scale for calculation (e.g., -1 to +1, with 0 as neutral, where 50 on the input scale becomes the neutral point).
    *   An eigenvector-based algorithm (similar to PageRank) calculates a **global trust score** for each user.
    *   The system also identifies **communities** within the network based on positive trust relationships.
    *   **Community-specific trust scores** are calculated, reflecting how trusted a user is *within* their own detected community.

4.  **Advanced Community Detection:**
    *   The system uses an enhanced community detection algorithm based on the Louvain method and structural balance theory.
    *   **Core Communities:** First, natural communities are detected based on who trusts whom, without specifying a fixed number of communities in advance.
    *   **Handling Isolated Users:** Users with no positive trust connections are intelligently assigned to communities based on:
        *   Who trusts them (if anyone)
        *   Who they trust (if anyone)
        *   Who distrusts them (applying the "enemy of my enemy" principle)
    *   This approach recognizes that the UFO/UAP community naturally clusters into belief-aligned groups without forcing artificial divisions.

5.  **Visualization & Access:**
    *   The processed data, including global scores, community assignments, and community-specific scores, is made available on a public website (GitHub Pages).
    *   The website features:
        *   A **Rankings Table:** Displays users sorted by their global trust score. Includes a dropdown to view scores from a specific community's perspective.
        *   A **Network Visualization:** Shows the trust relationships between users. Node sizes are based on trust scores. Includes a dropdown to view the network based on global scores or community-specific scores.

## Features

*   **Decentralized Trust:** Trust is assigned by individual users, not a central authority.
*   **New 0-100 Scoring Scale:** Intuitive scale where 50 is neutral, 0 is maximum distrust, and 100 is maximum trust.
*   **Global Trust Scores:** Overall reputation within the entire network.
*   **Community Detection:** Identifies natural clusters of users who trust each other.
*   **Smart Isolated User Handling:** Uses both positive and negative relationships to place users in appropriate communities.
*   **Community-Perspective Scores:** Allows viewing trust scores from within a specific community, revealing local influencers.
*   **Dynamic Network Visualization:** Interactive graph showing users and their trust links.
*   **Normalized Influence:** User ratings are normalized to ensure fair influence.

## How to Participate

To assign trust or distrust to a Twitter/X user, post a tweet with the following format:

**Standard Command:**
`#ufotrust @target_username <score>`

**When Replying to a User (optional @username in command):**
If your tweet is a direct reply to someone, you can omit their `@target_username` from the `#ufotrust` command. The system will automatically assign the score to the user you are replying to.

`#ufotrust <score>` (when used in a reply tweet)

**Examples:**

*   To strongly trust `@exampleuser` (standard command):
    `#ufotrust @exampleuser 90`
*   Replying to `@anotheruser` and assigning them strong trust (implicit target):
    `@anotheruser That's a great point! #ufotrust 85`
*   Replying to `@thirduser` and assigning them neutrality (implicit target):
    `@thirduser Interesting. #ufotrust 50`
*   Replying to `@fourthuser` and assigning them strong distrust (implicit target):
    `@fourthuser I disagree. #ufotrust 15`

Remember to use a score between 0 and 100 (0=max distrust, 50=neutral, 100=max trust).

## Technical Details

*   **Backend:** Python scripts for data collection (Twitter API via RapidAPI) and score calculation (NumPy, NetworkX).
*   **Community Detection:** Louvain modularity optimization on the positive-trust subgraph, with structural balance theory applied for isolated nodes.
*   **Automation:** PowerShell scripts for scheduling updates.
*   **Frontend:** HTML, CSS, JavaScript, Bootstrap, D3.js for visualization.
*   **Hosting:** GitHub Pages for the website, GitHub Actions for CI/CD (potentially).

## Disclaimer

This is an experimental system. Trust scores are based on subjective user assignments and algorithmic calculations. They should be considered one of many data points when evaluating information or users online. The system is open to gaming or manipulation, though measures are in place to mitigate this.
