#include <../tools.h>

/*! @brief Flag for checking if this header has already been included. */
#ifndef CISCOMMBASE_H_
#define CISCOMMBASE_H_

/*! @brief Communicator types. */
enum comm_enum { NULL_COMM, IPC_COMM, ZMQ_COMM,
		 RPC_COMM, SERVER_COMM, CLIENT_COMM,
		 ASCII_FILE_COMM, ASCII_TABLE_COMM, ASCII_TABLE_ARRAY_COMM };
typedef enum comm_enum comm_type;
#define COMM_NAME_SIZE 100
#define COMM_ADDRESS_SIZE 500
#define COMM_DIR_SIZE 100

/*!
  @brief Communication structure.
 */
typedef struct comm_t {
  comm_type type; //!< Comm type.
  char name[COMM_NAME_SIZE]; //!< Comm name.
  char address[COMM_ADDRESS_SIZE]; //!< Comm address.
  char direction[COMM_DIR_SIZE]; //!< send or recv for direction messages will go.
  int valid; //!< 1 if communicator initialized, 0 otherwise.
  void *handle; //!< Pointer to handle for comm.
  void *info; //!< Pointer to any extra info comm requires.
  seri_t serializer; //!< Serializer for comm messages.
  size_t maxMsgSize; //!< The maximum message size.
  int always_send_header; //!< 1 if comm should always send a header.
  int index_in_register; //!< Index of the comm in the comm register.
  time_t *last_send; //!< Clock output at time of last send.
  int *sent_eof; //!< Flag specifying if EOF has been sent
  void *reply; //!< Reply information.
} comm_t;


/*!
  @brief Initialize an empty comm base without malloc.
  @returns comm_t NULL comm object.
 */
static inline
comm_t empty_comm_base() {
  comm_t ret;
  ret.type = NULL_COMM;
  ret.address[0] = '\0';
  ret.direction[0] = '\0';
  ret.valid = 0;
  ret.handle = NULL;
  ret.info = NULL;
  ret.maxMsgSize = 0;
  ret.always_send_header = 0;
  ret.index_in_register = -1;
  ret.last_send = NULL;
  ret.sent_eof = NULL;
  return ret;
};

/*!
  @brief Initialize a basic communicator with address info.
  @param[in] address char * Address for new comm.
  @param[in] direction Direction that messages will go through the comm.
  Values include "recv" and "send".
  @param[in] t comm_type Type of comm that should be created.
  @param[in] seri_info Pointer to info for the serializer (e.g. format string).
  @returns comm_t* Address of comm structure.
*/
static inline
comm_t* new_comm_base(char *address, const char *direction, const comm_type t,
		      const void *seri_info) {
  comm_t* ret = (comm_t*)malloc(sizeof(comm_t));
  if (ret == NULL) {
    cislog_error("new_comm_base: Failed to malloc comm.");
    return ret;
  }
  ret->type = t;
  ret->valid = 1;
  ret->name[0] = '\0';
  if (address == NULL)
    ret->address[0] = '\0';
  else
    strcpy(ret->address, address);
  if (direction == NULL) {
    ret->direction[0] = '\0';
    ret->valid = 0;
  } else {
    strcpy(ret->direction, direction);
  }
  ret->handle = NULL;
  ret->info = NULL;
  if (seri_info == NULL) {
    ret->serializer.type = DIRECT_SERI;
    ret->serializer.info = seri_info;
  } else {
    ret->serializer.type = FORMAT_SERI;
    ret->serializer.info = seri_info;
  }
  ret->maxMsgSize = CIS_MSG_MAX;
  ret->always_send_header = 0;
  ret->index_in_register = -1;
  ret->last_send = (time_t*)malloc(sizeof(time_t));
  ret->last_send[0] = 0;
  ret->sent_eof = (int*)malloc(sizeof(int));
  ret->sent_eof[0] = 0;
  return ret;
};

/*!
  @brief Initialize a basic communicator.
  The name is used to locate the comm address stored in the associated
  environment variable.
  @param[in] name Name of environment variable that the queue address is
  stored in.
  @param[in] direction Direction that messages will go through the comm.
  Values include "recv" and "send".
  @param[in] t comm_type Type of comm that should be created.
  @param[in] seri_info Format for formatting/parsing messages.
  @returns comm_t* Address of comm structure.
 */
static inline
comm_t* init_comm_base(const char *name, const char *direction,
		       const comm_type t, const void *seri_info) {
  char full_name[COMM_NAME_SIZE];
  char *address = NULL;
  if (name != NULL) {
    strcpy(full_name, name);
    if (t != RPC_COMM) {
      if (strcmp(direction, "send") == 0)
	strcat(full_name, "_OUT");
      else if (strcmp(direction, "recv") == 0)
	strcat(full_name, "_IN");
    }
    address = getenv(full_name);
  }
  comm_t *ret = new_comm_base(address, direction, t, seri_info);
  if (ret == NULL) {
    return ret;
  }
  if (name == NULL) {
    ret->name[0] = '\0';
    ret->valid = 0;
  } else
    strcpy(ret->name, full_name);
  if ((strlen(ret->address) == 0) && (t != SERVER_COMM) && (t != CLIENT_COMM)) {
    cislog_error("init_comm_base: %s not registered as environment variable.\n",
		 full_name);
    ret->valid = 0;
  }
  cislog_debug("init_comm_base(%s): Done", ret->name);
  return ret;
};

/*!
  @brief Perform deallocation for basic communicator.
  @param[in] x comm_t * Pointer to communicator to deallocate.
  @returns int 1 if there is and error, 0 otherwise.
*/
static inline
int free_comm_base(comm_t *x) {
  if (x->last_send != NULL) {
    free(x->last_send);
    x->last_send = NULL;
  }
  if (x->sent_eof != NULL) {
    free(x->sent_eof);
    x->sent_eof = NULL;
  }
/*   // Prevent C4100 warning on windows by referencing param */
/* #ifdef _WIN32 */
/*   x; */
/* #endif */
  return 0;
};

/*!
  @brief Send a message to the comm.
  Send a message smaller than CIS_MSG_MAX bytes to an output comm. If the
  message is larger, it will not be sent.
  @param[in] x comm_t structure that comm should be sent to.
  @param[in] data character pointer to message that should be sent.
  @param[in] len size_t length of message to be sent.
  @returns int 0 if send succesfull, -1 if send unsuccessful.
 */
static inline
int comm_base_send(const comm_t x, const char *data, const size_t len) {
  // Prevent C4100 warning on windows by referencing param
#ifdef _WIN32
  x;
  data;
  len;
#endif
  // Make sure you arn't sending a message that is too big
  if (len > CIS_MSG_MAX) {
    cislog_error("comm_base_send(%s): message too large for single packet (CIS_MSG_MAX=%d, len=%d)",
		 x.name, CIS_MSG_MAX, len);
    return -1;
  }
  return 0;
};

  
#endif /*CISCOMMBASE_H_*/
