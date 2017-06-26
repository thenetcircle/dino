## Access Control Lists

### Custom ACL Pattern

A custom ACL pattern may be set instead of the regular simple ACL types. A simple grammar exists to specify this.

#### Grammar

    |   OR
    ,   AND
    !   NOT     (TODO)
    =   VALUE
    ()  GROUP

* AND has preference over OR,
* GROUP can be used to combine grammars,
* Nested parentheses are NOT allowed.

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

For escort channels, females should not be allowed to list the rooms, unless they have the `tg-p` membership type.
Everyone else can list and join:

    gender=!w|gender=w,membership=tg-p
