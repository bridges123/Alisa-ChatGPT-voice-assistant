#pragma once
/* One-shot question completion. Plain values only: no JSON, network or audio
 * dependency, so the decision can be tested on any host with a C++ compiler. */
struct OneShotAnswer {
    bool asked=false,heard=false;
    unsigned int audible_blocks=0;
    double silence_seconds=0;
};
// A spoken answer must actually be heard, be longer than the opening cue and
// be followed by a pause. The pause is a parameter because a "thinking"
// filler needs more room than a normal end of answer.
inline bool one_shot_complete(const OneShotAnswer &answer,double silence_seconds=2.0){
    return answer.asked&&answer.heard&&answer.audible_blocks>8&&answer.silence_seconds>=silence_seconds;
}
// Bound the whole call so a silent server cannot hold the station forever.
inline bool one_shot_timeout(double since_asked_seconds){
    return since_asked_seconds>=45.0;
}
