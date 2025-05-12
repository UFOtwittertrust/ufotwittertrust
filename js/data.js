// Trust system data
// Auto-generated on 2025-05-11 20:57:37
// DO NOT EDIT MANUALLY

const trustData = {
  "lastUpdated": "May 11, 2025 08:57 PM",
  "users": [
    {
      "username": "DanHaug6",
      "trustScore": 0.08321947889135548,
      "trustors": 1,
      "trustees": 0,
      "interests": [],
      "communityId": 3
    },
    {
      "username": "GoodTroubleShow",
      "trustScore": 0.08411663382999816,
      "trustors": 2,
      "trustees": 0,
      "interests": [],
      "communityId": 3
    },
    {
      "username": "Halsrethink",
      "trustScore": 0.08679561553406524,
      "trustors": 1,
      "trustees": 0,
      "interests": [],
      "communityId": 3
    },
    {
      "username": "MiddleofMayhem",
      "trustScore": 0.07261668427258146,
      "trustors": 1,
      "trustees": 0,
      "interests": [],
      "communityId": 1
    },
    {
      "username": "PTHellyer",
      "trustScore": 0.07289881784521883,
      "trustors": 1,
      "trustees": 0,
      "interests": [],
      "communityId": 2
    },
    {
      "username": "ShipsSmall",
      "trustScore": 0.10539152607615603,
      "trustors": 2,
      "trustees": 0,
      "interests": [],
      "communityId": 4
    },
    {
      "username": "TheOfficialQF",
      "trustScore": 0.08278256535333636,
      "trustors": 2,
      "trustees": 0,
      "interests": [],
      "communityId": 3
    },
    {
      "username": "cosmic_surplus",
      "trustScore": 0.09913328695141393,
      "trustors": 1,
      "trustees": 0,
      "interests": [],
      "communityId": 4
    },
    {
      "username": "jayanderson",
      "trustScore": 0.07851373162428978,
      "trustors": 2,
      "trustees": 0,
      "interests": [],
      "communityId": 3
    },
    {
      "username": "susangerbic",
      "trustScore": 0.08811906703804853,
      "trustors": 2,
      "trustees": 0,
      "interests": [],
      "communityId": 4
    },
    {
      "username": "ufobeliever1947",
      "trustScore": 0.07320629629176813,
      "trustors": 0,
      "trustees": 8,
      "interests": [],
      "communityId": 3
    },
    {
      "username": "ufoskeptic1968",
      "trustScore": 0.07320629629176813,
      "trustors": 0,
      "trustees": 7,
      "interests": [],
      "communityId": 4
    }
  ],
  "relationships": [
    {
      "source": "ufobeliever1947",
      "target": "DanHaug6",
      "value": 3.0898227107438614
    },
    {
      "source": "ufobeliever1947",
      "target": "GoodTroubleShow",
      "value": 3.5312259551358416
    },
    {
      "source": "ufobeliever1947",
      "target": "Halsrethink",
      "value": 4.193330821723812
    },
    {
      "source": "ufobeliever1947",
      "target": "MiddleofMayhem",
      "value": -4.414032443919802
    },
    {
      "source": "ufobeliever1947",
      "target": "ShipsSmall",
      "value": 3.5312259551358416
    },
    {
      "source": "ufobeliever1947",
      "target": "TheOfficialQF",
      "value": 3.0898227107438614
    },
    {
      "source": "ufobeliever1947",
      "target": "jayanderson",
      "value": 1.7656129775679208
    },
    {
      "source": "ufobeliever1947",
      "target": "susangerbic",
      "value": -3.972629199527822
    },
    {
      "source": "ufoskeptic1968",
      "target": "GoodTroubleShow",
      "value": -3.452612025890616
    },
    {
      "source": "ufoskeptic1968",
      "target": "PTHellyer",
      "value": -2.301741350593744
    },
    {
      "source": "ufoskeptic1968",
      "target": "ShipsSmall",
      "value": 4.603482701187488
    },
    {
      "source": "ufoskeptic1968",
      "target": "TheOfficialQF",
      "value": -2.87717668824218
    },
    {
      "source": "ufoskeptic1968",
      "target": "cosmic_surplus",
      "value": 5.75435337648436
    },
    {
      "source": "ufoskeptic1968",
      "target": "jayanderson",
      "value": -2.87717668824218
    },
    {
      "source": "ufoskeptic1968",
      "target": "susangerbic",
      "value": 3.452612025890616
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
