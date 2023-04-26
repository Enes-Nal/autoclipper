import java.util.ArrayList;
class school{
  public int i = 34;

  public school(int i) {
      this.i = i;
  }
  public static void main(String[] args) {
    school x = new school(90), y = new school(7);
y = x;
y.i = 65;
System.out.println(x.i);
  }
}











      //       int[] values = {1, 2, 3, 4, 5};

// // loop 1
// for (int j = 0; j < values.length - 1; j++)
//     values[j]++;
//     for (int i : values) {
//         System.out.print(i + " ");
//     }
//     }
//   }
    



    // public static void main(String[] args) {
    //   int a = 13;
    //   int b = 0;
  
    //   for (int c = 3; c <= 6; c++) {
    //     b = 0;
    //     while (b < c) {
    //       b = b + 1;
    //       a = a + b;
    //     }
    //     b = b + a;
    //   }
    //   System.out.print(b);
    // }