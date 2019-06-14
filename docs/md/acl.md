## Access Control Lists

### Available `acl_type`s

- age
- gender
- membership
- group
- country
- city
- image
- has_webcam
- fake_checked
- owner
- admin
- room_owner
- moderator
- superuser
- crossroom
- samechannel
- sameroom
- disallow
- custom

For custom, see [Custom ACL Pattern](acl.md#custom-acl-pattern) below.

### Available `actions`

For rooms, the actions are:

- join
- setacl
- history
- create
- list
- kick
- message
- crossroom
- ban
- autojoin

And for channels:

- create
- setacl
- list
- create
- message
- crossroom
- ban
- whisper

### Custom ACL Pattern

A custom ACL pattern may be set instead of the regular simple ACL types. A simple grammar exists to specify this.

#### Grammar

    |   OR
    ,   AND
    !   NOT
    =   VALUE
    ()  GROUP

* AND has preference over OR,
* GROUP can be used to combine grammars,
* Nested parentheses are NOT allowed.

Since AND has preference over OR, two or more OR clauses can be grouped using parentheses so avoid an AND clause taking
over, same as with boolean logic:

    a: true
    b: false
    c: true

    a & b | c => false          age=35,gender=f|membership=normal
    b & (b | c) => true         age=35,(gender=f|membership=normal)

#### Examples

Either the user is 35 years or older, OR the user is a female and less than (or equal to) 26 years old:

    age=35:|gender=f,age:26
    
Parenthesis may be used to group or clauses before and clauses (since AND has priority before OR), as in this example,
 if the user is a female or above the age of 35 (inclusive) he/she will be allowed to join, as long as he/she ALSO is
 NOT a normal account.

    (age=35:|gender=f),membership=!normal
    
Compare with the same without parenthesis, where the AND would take priority over the OR; as long as the user is above
35 (inclusive) he/she'll be allowed to join. If less than 35, he/she can still join if BOTH female and NOT normal 
account.

    age=35:|gender=f,membership=!normal

For some channels, maybe females should not be allowed to list the rooms, unless they have the `paying` membership type.
In this case we can negate the values to allow everything except the specified one. Everyone else can list and join:

    gender=!f|gender=f,membership=paying
