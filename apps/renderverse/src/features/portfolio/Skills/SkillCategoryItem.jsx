import styles from "./Skills.module.css";
import Rating from "./Rating";
import PropTypes from "prop-types";

const SkillCategoryItem = ({ item }) => {
  const { name, rating } = item;
  return (
    <li className={styles.item}>
      {name}
      <Rating size="0.6em" checked={rating} />
    </li>
  );
};

SkillCategoryItem.propTypes = {
  item: PropTypes.object,
};

export default SkillCategoryItem;
