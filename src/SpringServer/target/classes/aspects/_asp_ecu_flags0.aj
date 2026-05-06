package aspects;

import bridge.EcuSample;
import bridge.JavaMonitorBridge;

import larva.*;
public aspect _asp_ecu_flags0 {

public static Object lock = new Object();

boolean initialized = false;

after():(staticinitialization(*)){
if (!initialized){
	initialized = true;
	_cls_ecu_flags0.initialize();
}
}
before ( EcuSample s) : (call(* *.onSample(..)) && args(s) && !cflow(adviceexecution()) && !cflow(within(larva.*))  && !(within(larva.*))) {

synchronized(_asp_ecu_flags0.lock){

_cls_ecu_flags0 _cls_inst = _cls_ecu_flags0._get_cls_ecu_flags0_inst();
_cls_inst.s = s;
_cls_inst._call(thisJoinPoint.getSignature().toString(), 0/*sampleReceived*/);
_cls_inst._call_all_filtered(thisJoinPoint.getSignature().toString(), 0/*sampleReceived*/);
}
}
}