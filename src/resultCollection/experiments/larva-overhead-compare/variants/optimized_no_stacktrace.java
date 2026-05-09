package larva;


import bridge.EcuSample;

import java.util.LinkedHashMap;
import java.io.PrintWriter;

public class _cls_ecu_flags0 implements _callable{

public static PrintWriter pw; 
public static _cls_ecu_flags0 root;
private static boolean MONITOR_LOGGING_ENABLED = Boolean.getBoolean("rd2.monitor.logging");

public static LinkedHashMap<_cls_ecu_flags0,_cls_ecu_flags0> _cls_ecu_flags0_instances;

_cls_ecu_flags0 parent; //to remain null - this class does not have a parent!
public static EcuSample s;
int no_automata;

int _state_id_ecuSafety;
 public boolean initialized =false ;
 public double prevThrottle =0.0 ;
 public double prevRunTime =0.0 ;
 public double prevLoad =0.0 ;
 public double prevMapSource =0.0 ;

public static void initialize(){
//note that this initialisation does not include user-defined declarations in the Variables section


_cls_ecu_flags0_instances = new LinkedHashMap<_cls_ecu_flags0,_cls_ecu_flags0>();
try{
root = new _cls_ecu_flags0();
_cls_ecu_flags0_instances.put(root, root);
  root.initialisation();
}catch(Exception ex)
{ex.printStackTrace();}
}
//inheritance could not be used because of the automatic call to super()
//when the constructor is called...we need to keep the SAME parent if this exists!

public _cls_ecu_flags0() {
}

public void initialisation() {
no_automata = 1;
//initialise automata
_state_id_ecuSafety = 5;


}

public static _cls_ecu_flags0 _get_cls_ecu_flags0_inst() { synchronized(_cls_ecu_flags0_instances){
 return root;
}
}

private static void monitorLog(String msg) {
if (MONITOR_LOGGING_ENABLED) {
System.out.println(msg);
}
}

public String getCurrentStateName() {
return _string_ecuSafety(_state_id_ecuSafety, 0);
}

public boolean isInBadState() {
return _state_id_ecuSafety != 5;
}

public boolean equals(Object o) {
 if ((o instanceof _cls_ecu_flags0))
{return true;}
else
{return false;}
}

public int hashCode() {
return 1;
}

public void _call(String _info, int... _event){
synchronized(_cls_ecu_flags0_instances){
_performLogic_ecuSafety(_info, _event);
}
}

public void _call_all_filtered(String _info, int... _event){
}

public static void _call_all(String _info, int... _event){

_cls_ecu_flags0[] a = new _cls_ecu_flags0[1];
synchronized(_cls_ecu_flags0_instances){
a = _cls_ecu_flags0_instances.keySet().toArray(a);}
for (_cls_ecu_flags0 _inst : a)

if (_inst != null) _inst._call(_info, _event);
}

public void _killThis(){
try{
if (--no_automata == 0){
synchronized(_cls_ecu_flags0_instances){
_cls_ecu_flags0_instances.remove(this);}
}
else if (no_automata < 0)
{throw new Exception("no_automata < 0!!");}
}catch(Exception ex){ex.printStackTrace();}
}


public void _performLogic_ecuSafety(String _info, int... _event) {

if (0==1){}
else if (_state_id_ecuSafety==4){
		if (1==0){}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (true )){
		prevThrottle =s .ThrottlePosition ;
prevRunTime =s .EngineRunningTime ;
prevLoad =s .Load ;
prevMapSource =s .MAPSource ;

		_state_id_ecuSafety = 5;//moving to state ok

		_goto_ecuSafety(_info);
		}
}
else if (_state_id_ecuSafety==0){
		if (1==0){}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (true )){
		prevThrottle =s .ThrottlePosition ;
prevRunTime =s .EngineRunningTime ;
prevLoad =s .Load ;
prevMapSource =s .MAPSource ;

		_state_id_ecuSafety = 5;//moving to state ok

		_goto_ecuSafety(_info);
		}
}
else if (_state_id_ecuSafety==2){
		if (1==0){}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (true )){
		prevThrottle =s .ThrottlePosition ;
prevRunTime =s .EngineRunningTime ;
prevLoad =s .Load ;
prevMapSource =s .MAPSource ;

		_state_id_ecuSafety = 5;//moving to state ok

		_goto_ecuSafety(_info);
		}
}
else if (_state_id_ecuSafety==3){
		if (1==0){}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (true )){
		prevThrottle =s .ThrottlePosition ;
prevRunTime =s .EngineRunningTime ;
prevLoad =s .Load ;
prevMapSource =s .MAPSource ;

		_state_id_ecuSafety = 5;//moving to state ok

		_goto_ecuSafety(_info);
		}
}
else if (_state_id_ecuSafety==5){
		if (1==0){}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (!initialized )){
		initialized =true ;
prevThrottle =s .ThrottlePosition ;
prevRunTime =s .EngineRunningTime ;
prevLoad =s .Load ;
prevMapSource =s .MAPSource ;

		_state_id_ecuSafety = 5;//moving to state ok

		_goto_ecuSafety(_info);
		}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (initialized &&(s .EngineRunningTime <prevRunTime ))){
		monitorLog("[LARVA][RD2] TIME_BACKWARDS prev="+prevRunTime +" curr="+s .EngineRunningTime );

		_state_id_ecuSafety = 0;//moving to state timeBackwards

		_goto_ecuSafety(_info);
		}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (initialized &&(s .RPM >900.0 )&&((s .BatteryVoltage_V <11.5 )||(s .BatteryVoltage_V >15.5 )))){
		monitorLog("[LARVA][RD2] VOLTAGE_OUT_OF_RANGE v="+s .BatteryVoltage_V +" rpm="+s .RPM );

		_state_id_ecuSafety = 1;//moving to state voltageOutOfRange

		_goto_ecuSafety(_info);
		}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (initialized &&(s .CoolantTemp_C >110.0 ))){
		monitorLog("[LARVA][RD2] COOLANT_TOO_HIGH C="+s .CoolantTemp_C );

		_state_id_ecuSafety = 2;//moving to state coolantTooHigh

		_goto_ecuSafety(_info);
		}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (initialized &&((s .EngineRunningTime -prevRunTime )>0.0 )&&((s .EngineRunningTime -prevRunTime )<=0.2 )&&(Math .abs (s .ThrottlePosition -prevThrottle )>25.0 ))){
		monitorLog("[LARVA][RD2] THROTTLE_SPIKE dThrottle="+Math .abs (s .ThrottlePosition -prevThrottle )+" dt="+(s .EngineRunningTime -prevRunTime ));

		_state_id_ecuSafety = 3;//moving to state throttleSpike

		_goto_ecuSafety(_info);
		}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (initialized &&(Math .abs (s .Load -s .MAPSource )>60.0 ))){
		monitorLog("[LARVA][RD2] LOAD_MAP_MISMATCH load="+s .Load +" map="+s .MAPSource );

		_state_id_ecuSafety = 4;//moving to state loadMapMismatch

		_goto_ecuSafety(_info);
		}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (initialized )){
		prevThrottle =s .ThrottlePosition ;
prevRunTime =s .EngineRunningTime ;
prevLoad =s .Load ;
prevMapSource =s .MAPSource ;

		_state_id_ecuSafety = 5;//moving to state ok

		_goto_ecuSafety(_info);
		}
}
else if (_state_id_ecuSafety==1){
		if (1==0){}
		else if ((_occurredEvent(_event,0/*sampleReceived*/)) && (true )){
		prevThrottle =s .ThrottlePosition ;
prevRunTime =s .EngineRunningTime ;
prevLoad =s .Load ;
prevMapSource =s .MAPSource ;

		_state_id_ecuSafety = 5;//moving to state ok

		_goto_ecuSafety(_info);
		}
}
}

public void _goto_ecuSafety(String _info){
 if (!MONITOR_LOGGING_ENABLED) {
   return;
 }
 String state_format = _string_ecuSafety(_state_id_ecuSafety, 1);
 if (state_format.startsWith("!!!SYSTEM REACHED BAD STATE!!!")) {
   monitorLog("[ecuSafety]MOVED ON METHODCALL: "+ _info +" TO STATE::> " + state_format);
}
}

public String _string_ecuSafety(int _state_id, int _mode){
switch(_state_id){
case 4: if (_mode == 0) return "loadMapMismatch"; else return "!!!SYSTEM REACHED BAD STATE!!! loadMapMismatch ";
case 0: if (_mode == 0) return "timeBackwards"; else return "!!!SYSTEM REACHED BAD STATE!!! timeBackwards ";
case 2: if (_mode == 0) return "coolantTooHigh"; else return "!!!SYSTEM REACHED BAD STATE!!! coolantTooHigh ";
case 3: if (_mode == 0) return "throttleSpike"; else return "!!!SYSTEM REACHED BAD STATE!!! throttleSpike ";
case 1: if (_mode == 0) return "voltageOutOfRange"; else return "!!!SYSTEM REACHED BAD STATE!!! voltageOutOfRange ";
case 5: if (_mode == 0) return "ok"; else return "ok";
default: return "!!!SYSTEM REACHED AN UNKNOWN STATE!!!";
}
}

public boolean _occurredEvent(int[] _events, int event){
for (int i:_events) if (i == event) return true;
return false;
}
}