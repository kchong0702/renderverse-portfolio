import styles from "./Rating.module.css";
import { FaStar } from "react-icons/fa6";
import PropTypes from "prop-types";

const Rating = ({ size, checked }) => {
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

Rating.propTypes = {
  size: PropTypes.number,
  checked: PropTypes.number,
};

export default Rating;
