// Trust system data
// Auto-generated on 2025-05-11 20:48:34
// DO NOT EDIT MANUALLY

const trustData = {
  "lastUpdated": "May 11, 2025 08:47 PM",
  "users": [
    {
      "username": "DanHaug6",
      "trustScore": 0.0985485372207531,
      "trustors": 1,
      "trustees": 0,
      "interests": [],
      "communityId": 1
    },
    {
      "username": "GoodTroubleShow",
      "trustScore": 0.10039158686098383,
      "trustors": 1,
      "trustees": 0,
      "interests": [],
      "communityId": 1
    },
    {
      "username": "Halsrethink",
      "trustScore": 0.10315616132132992,
      "trustors": 1,
      "trustees": 0,
      "interests": [],
      "communityId": 1
    },
    {
      "username": "PTHellyer",
      "trustScore": 0.08513594436874501,
      "trustors": 1,
      "trustees": 0,
      "interests": [],
      "communityId": 2
    },
    {
      "username": "ShipsSmall",
      "trustScore": 0.13274734721170095,
      "trustors": 2,
      "trustees": 0,
      "interests": [],
      "communityId": 3
    },
    {
      "username": "TheOfficialQF",
      "trustScore": 0.09781323672266296,
      "trustors": 2,
      "trustees": 0,
      "interests": [],
      "communityId": 1
    },
    {
      "username": "cosmic_surplus",
      "trustScore": 0.12609189017753447,
      "trustors": 1,
      "trustees": 0,
      "interests": [],
      "communityId": 3
    },
    {
      "username": "susangerbic",
      "trustScore": 0.0848209166380135,
      "trustors": 1,
      "trustees": 0,
      "interests": [],
      "communityId": 4
    },
    {
      "username": "ufobeliever1947",
      "trustScore": 0.08564718973913807,
      "trustors": 0,
      "trustees": 6,
      "interests": [],
      "communityId": 1
    },
    {
      "username": "ufoskeptic1968",
      "trustScore": 0.08564718973913807,
      "trustors": 0,
      "trustees": 4,
      "interests": [],
      "communityId": 3
    }
  ],
  "relationships": [
    {
      "source": "ufobeliever1947",
      "target": "DanHaug6",
      "value": 3.512093643699515
    },
    {
      "source": "ufobeliever1947",
      "target": "GoodTroubleShow",
      "value": 4.01382130708516
    },
    {
      "source": "ufobeliever1947",
      "target": "Halsrethink",
      "value": 4.766412802163628
    },
    {
      "source": "ufobeliever1947",
      "target": "ShipsSmall",
      "value": 4.01382130708516
    },
    {
      "source": "ufobeliever1947",
      "target": "TheOfficialQF",
      "value": 3.512093643699515
    },
    {
      "source": "ufobeliever1947",
      "target": "susangerbic",
      "value": -4.515548970470806
    },
    {
      "source": "ufoskeptic1968",
      "target": "PTHellyer",
      "value": -2.793721183078313
    },
    {
      "source": "ufoskeptic1968",
      "target": "ShipsSmall",
      "value": 5.587442366156626
    },
    {
      "source": "ufoskeptic1968",
      "target": "TheOfficialQF",
      "value": -3.4921514788478913
    },
    {
      "source": "ufoskeptic1968",
      "target": "cosmic_surplus",
      "value": 6.984302957695783
    }
  ],
  "communities": [
    {
      "id": 1,
      "name": "Community A",
      "color": "#4285F4"
    },
    {
      "id": 2,
      "name": "Community B",
      "color": "#EA4335"
    },
    {
      "id": 3,
      "name": "Community C",
      "color": "#FBBC05"
    },
    {
      "id": 4,
      "name": "Community D",
      "color": "#34A853"
    }
  ]
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
