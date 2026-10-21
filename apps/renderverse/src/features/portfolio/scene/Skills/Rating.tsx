import styles from "./Rating.module.css";
import { FaStar } from "react-icons/fa6";

interface RatingProps {
  size: number | string;
  checked: number;
}

const Rating = ({ size, checked }: RatingProps) => {
  return (
    <div className={styles.container}>
      <FaStar className={checked > 0 ? styles.checked : ""} size={size} />
      <FaStar className={checked > 1 ? styles.checked : ""} size={size} />
      <FaStar className={checked > 2 ? styles.checked : ""} size={size} />
      <FaStar className={checked > 3 ? styles.checked : ""} size={size} />
      <FaStar className={checked > 4 ? styles.checked : ""} size={size} />
    </div>
  );
};

export default Rating;
