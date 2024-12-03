import java.util.Scanner;

public class p2 {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        System.out.print("Enter a string to reverse: ");
        String input = scanner.nextLine();

        String reversed = new StringBuilder(input).reverse().toString();
        System.out.println("Reversed string: " + reversed);
    }
}
