// Trust system data
// Auto-generated on [RESET]
// DO NOT EDIT MANUALLY

const trustData = {
  "lastUpdated": "",
  "users": [],
  "relationships": [],
  "communities": []
};

// Map to quickly look up users by username
const userMap = {};
trustData.users.forEach(user => {
    userMap[user.username] = user;
});

// Function to get user details
function getUserDetails(username) {
    return userMap[username];
}

// Function to get incoming trust relationships for a user
function getIncomingTrust(username) {
    return trustData.relationships.filter(rel => rel.target === username);
}

// Function to get outgoing trust relationships for a user
function getOutgoingTrust(username) {
    return trustData.relationships.filter(rel => rel.source === username);
}

// Function to get community color for a user
function getUserCommunityColor(username) {
    const user = getUserDetails(username);
    if (!user) return "#999999";
    const community = trustData.communities.find(c => c.id === user.communityId);
    return community ? community.color : "#999999";
}
