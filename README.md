# Mailman LDAP Members Plugin

This is a Mailman Plugin that enables you to have list members derived from an LDAP
group.

However, there are a few caveats: 
- You won't see the LDAP Members in the Member list
- LDAP Members can't have any special settings like digests, language etc.
- LDAP Members can't unsubscribe
- LDAP Members are constraint to the default member-processing Action. No custom action/posting privileges per user
- Bounce Processing for LDAP Members will likely not work