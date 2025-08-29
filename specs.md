CallDNS is a system that works above the present voip and communication layers to verify the caller. This is in response to the challenges of deepfakes and SS7 issues in the wider communications infrastructure. 

The idea is that when the caller initiates a call to the callee there is a zero knowledge proof that gets generated that can be verfied by the reciever. The key idea is that the caller is able to broadcast something that can be next to realtime verified. 

Now this should be able to work across a call center to a app, a call center to a user with the callDNS app installed, a user to a user. All of this while ensure we callDNA cannot identify the originator and the reciever. This means that a caller can issue multiple calls, and a verifier can reall all the call zk and get one validation. 

This should have a device sdk that we can use to initiate and verify. 
