
// Flaps holding box

$fn = 50;

w=36;
d=12;
wall=1.2;


for ( y = [0 : 5] ){
  for ( x = [0 : 10] ){
   translate([y*(w-wall),0,x*(d-wall)])
   box();
   }
 }

module box(){
difference(){
translate([0,15,0])
cube([w,15,d], center=true);

translate([0,13,0])
cube([w-(wall*2),15,d-(wall*2)], center=true);

}
}



//linear_extrude(h=(3*0.16))
//import("flap.dxf");