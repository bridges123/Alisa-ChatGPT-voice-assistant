#include "voice_state.hpp"
#include <cassert>
#include <iostream>

using json=nlohmann::json;

int main(){
    VoiceServerState call;
    assert(call.can_start_audio(false));
    assert(!call.can_start_audio(true));
    assert(!call.receive("startup_telemetry",json::object()));
    assert(!call.receive("state_update",{{"new_state","listening"}}));
    assert(call.last_state=="listening");
    // Issue #14: goodbye can arrive while the opening cue is playing, before
    // any microphone/audio frames. Once it arrives, readiness stays forbidden.
    assert(call.receive("goodbye",{{"reason","error"},{"detail","internal_error"}}));
    assert(!call.can_start_audio(false));
    assert(call.error=="voice_server_internal_error");
    assert(call.close==json({{"reason","error"},{"detail","internal_error"}}));
    assert(call.receive("state_update",{{"new_state","listening"}}));
    assert(!call.can_start_audio(false));
    assert(call.receive("goodbye",{{"reason","normal"}}));
    assert(call.error=="voice_server_internal_error");

    for(auto mapping:{std::pair{"upstream_error","voice_server_upstream_error"},
                      std::pair{"server_error","voice_server_error"}}){
        VoiceServerState other;
        assert(other.receive("goodbye",{{"reason","error"},{"detail",mapping.first}}));
        assert(other.error==mapping.second);
    }
    VoiceServerState cap;
    assert(cap.receive("goodbye",{{"reason","cap_reached"},{"detail","internal_error"}}));
    assert(cap.error=="voice_daily_limit_reached");
    for(auto kind:{"error","session.error"}){
        VoiceServerState other;
        assert(other.receive(kind,json::object()));
        assert(other.error=="voice_session_ended");
        assert(!other.can_start_audio(false));
    }
    const std::string secret="cookie=private; account=hidden@example.test";
    for(const json &value:json::array({nullptr,false,42,1.5,json::array({"internal_error"}),
                                      json{{"detail","internal_error"}},secret,std::string(300000,'x')})){
        VoiceServerState other;
        assert(!other.receive("state_update",{{"new_state",value}}));
        assert(other.last_state=="unknown");
        // Incorrect reason types must still end the call, not get swallowed
        // by an exception and leave the caller waiting indefinitely.
        assert(other.receive("goodbye",{{"reason",value},{"detail",value}}));
        assert(other.close==json({{"reason","unknown"},{"detail","unknown"}}));
        assert(other.error=="voice_session_ended");
        assert(!other.can_start_audio(false));
        assert(other.close.dump().find(secret)==std::string::npos);
    }
    for(const json &payload:json::array({nullptr,false,42,"arbitrary",json::array()})){
        VoiceServerState other;
        assert(other.receive("goodbye",payload));
        assert(other.error=="voice_session_ended");
    }
    // One-shot question: only stop on a real spoken answer followed by a
    // pause. Never stop on silence alone, and never wait forever.
    OneShotAnswer answer;
    assert(!one_shot_complete(answer));
    answer.asked=true;answer.audible_blocks=40;answer.silence_seconds=9;
    assert(!one_shot_complete(answer));
    answer.heard=true;answer.silence_seconds=1.9;
    assert(!one_shot_complete(answer));
    answer.silence_seconds=2.0;
    assert(one_shot_complete(answer));
    answer.audible_blocks=8;
    assert(!one_shot_complete(answer));
    answer.audible_blocks=9;answer.silence_seconds=2.4;
    assert(one_shot_complete(answer));
    assert(!one_shot_timeout(0));
    assert(!one_shot_timeout(44.9));
    assert(one_shot_timeout(45.0));
    {
        // A short answer that is still arriving must not be cut at 2 s.
        OneShotAnswer early;
        early.asked=true;early.heard=true;early.audible_blocks=30;early.silence_seconds=0.2;
        assert(!one_shot_complete(early));
    }
    std::cout<<"voice close codes, terminal readiness, redaction and one-shot completion: passed\n";
}
