# Frequently Asked Questions
###### By myself, mostly (I forget)

## API
### General
Matches endpoint gets rewritten the moment a new round starts. This is usually 10-15 seconds after last match in that room ended.

A player leaving a room *where they have been playing alone* before the Game Over screen will result in that round not getting registered.


### About the `isOfficial` and `cheeseRows` properties

- `isOfficial` 
: It's true only when the match was played on FFA, Rookie playground or Cheese factory
- `cheeseRows`: The number of rows of cheese a player had left. So 0 would mean all of the cheese was eaten, if it wasn't because **players that go AFK will** also **get 0 in this property.**

### About the `team` property
The team a player has been playing in:

- `null`: No team.
- `0`: Team Red.
- `1`: Team Yellow.
- `2`: Team Green.
- `3`: Team Yellow.

### About the `ruleset` property
The mode the match has been played in:

- `0`: Standard.
- `1`: Cheese.
- `2`: Survivor.
- `3`: Slowest Link.
- `4`: 40 Lines.


## About the bot
### Does matches with no opponents count?

