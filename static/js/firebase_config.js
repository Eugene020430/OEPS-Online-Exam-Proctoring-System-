
// Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyBuQ0gTZKaEojtIb1_G_GT6dz2Qtk0w3_0",
    authDomain: "oeps-1.firebaseapp.com",
    projectId: "oeps-1",
    storageBucket: "oeps-1.firebasestorage.app",
    messagingSenderId: "158032806965",
    appId: "1:158032806965:web:5d777c126bddca74641d7c",
  };
  
  // Initialize Firebase
  firebase.initializeApp(firebaseConfig);
  
  // Get a reference to the services
  const db = firebase.firestore();
  const storage = firebase.storage();
  const auth = firebase.auth();