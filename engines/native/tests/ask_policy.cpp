/* One-shot completion policy. No JSON, network or account: runs anywhere. */
#include "ask_policy.hpp"
#include <cassert>
#include <cstdio>

int main(){
    OneShotAnswer answer;
    assert(!one_shot_complete(answer));                 // nothing heard yet
    answer.asked=true;answer.audible_blocks=40;answer.silence_seconds=9;
    assert(!one_shot_complete(answer));                 // only silence
    answer.heard=true;answer.silence_seconds=1.9;
    assert(!one_shot_complete(answer));                 // pause too short
    answer.silence_seconds=2.0;
    assert(one_shot_complete(answer));
    answer.audible_blocks=8;
    assert(!one_shot_complete(answer));                 // opening cue only
    answer.audible_blocks=9;answer.silence_seconds=2.4;
    assert(one_shot_complete(answer));
    assert(!one_shot_timeout(0));
    assert(!one_shot_timeout(44.9));
    assert(one_shot_timeout(45.0));
    // An answer that is still arriving must not be cut at 2 seconds.
    OneShotAnswer early;
    early.asked=true;early.heard=true;early.audible_blocks=30;early.silence_seconds=0.2;
    assert(!one_shot_complete(early));
    std::printf("one-shot completion and timeout: passed\n");
}
