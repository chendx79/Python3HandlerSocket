#include <Python.h>


#define END_ENCODABLE_CHAR 0x0f
#define END_ENCODED_CHAR 0x4f
#define ENCODING_SHIFT 0x40
#define ENCODING_PREFIX 0x01

struct str_t {
    unsigned int char_length;
    const char *raw_end;
};

int init_string_data(PyObject *raw_data, struct str_t *string_data) {
    if (PyUnicode_Check(raw_data)) {
        string_data->char_length = sizeof(Py_UNICODE);
        string_data->raw_end = (const char*)(PyUnicode_AS_UNICODE(raw_data) + PyUnicode_GET_SIZE(raw_data));
    } else if (PyString_Check(raw_data)) {
        string_data->char_length = 1;
        string_data->raw_end = PyString_AS_STRING(raw_data) + PyString_GET_SIZE(raw_data);
    } else {
        return 0;
    }

    return 1;
}

char* get_string(PyObject *raw_data, struct str_t *string_data) {
    if (string_data->char_length > 1) {
        return (char*)PyUnicode_AS_UNICODE(raw_data);
    } else {
        return PyString_AS_STRING(raw_data);
    }
}

unsigned int get_num_encoded_chars(PyObject *raw_data, struct str_t *string_data, short encode) {
    unsigned int num_chars = 0;
    char *str_raw = get_string(raw_data, string_data);

    while (*str_raw || str_raw < string_data->raw_end) {
        if ((encode && *str_raw >= 0 && *str_raw <= END_ENCODABLE_CHAR) ||
                (!encode && *str_raw == ENCODING_PREFIX 
                 && *(str_raw+string_data->char_length) >= ENCODING_SHIFT
                 && *(str_raw+string_data->char_length) <= END_ENCODED_CHAR)) {
            num_chars++;
        }
        str_raw += string_data->char_length;
    }

    return num_chars;
}

void copy_ending(PyObject *raw_data, char *target, char *source, struct str_t *string_data) {
    if (source < string_data->raw_end) {
        Py_ssize_t diff;
        if (string_data->char_length > 1) {
            diff = PyUnicode_GET_DATA_SIZE(raw_data) - (source - (char*)PyUnicode_AS_UNICODE(raw_data));
        } else {
            diff = PyString_GET_SIZE(raw_data) - (source - PyString_AS_STRING(raw_data));
        }
        Py_MEMCPY(target, source, diff);
    }
}

static PyObject* encode(PyObject *self, PyObject *raw_data) {
    PyObject *encoded;
    unsigned int num_chars = 0;
    struct str_t string_data;
    char *str_raw;
    char *str_enc;

    if (!init_string_data(raw_data, &string_data)) {
        return NULL;
    }

    num_chars = get_num_encoded_chars(raw_data, &string_data, 1);

    if (!num_chars) {
        Py_INCREF(raw_data);
        return raw_data;
    }

    if (string_data.char_length > 1) {
        encoded = PyUnicode_FromUnicode(NULL, PyUnicode_GET_SIZE(raw_data) + num_chars);
    } else {
        encoded = PyString_FromStringAndSize(NULL, PyString_GET_SIZE(raw_data) + num_chars);
    }
    if (!encoded) {
        return NULL;
    }
    str_raw = get_string(raw_data, &string_data);
    str_enc = get_string(encoded, &string_data);

    while (num_chars--) {
        char *next = str_raw;
        while (next < string_data.raw_end) {
            if (*next >= 0 && *next <= END_ENCODABLE_CHAR) {
                break;
            }
            next += string_data.char_length;
        }

        if (next > str_raw) {
            Py_MEMCPY(str_enc, str_raw, next - str_raw);
            str_enc += next - str_raw;
        }

        if (string_data.char_length > 1) {
            int i;
            for (i = 0; i < 2*string_data.char_length; i++) {
                str_enc[i] = 0;
            }
        }
        str_enc[0] = ENCODING_PREFIX;
        str_enc[string_data.char_length] = (*next) | ENCODING_SHIFT;
        str_enc += 2*string_data.char_length;

        str_raw = next + string_data.char_length;
    }

    copy_ending(raw_data, str_enc, str_raw, &string_data);

    return encoded;
}

static PyObject* decode(PyObject *self, PyObject *raw_data) {
    PyObject *decoded;
    unsigned int num_chars = 0;
    struct str_t string_data;
    char *str_raw;
    char *str_dec;

    if (!init_string_data(raw_data, &string_data)) {
        return NULL;
    }

    num_chars = get_num_encoded_chars(raw_data, &string_data, 0);

    if (!num_chars) {
        Py_INCREF(raw_data);
        return raw_data;
    }

    if (string_data.char_length > 1) {
        decoded = PyUnicode_FromUnicode(NULL, PyUnicode_GET_SIZE(raw_data) - num_chars);
    } else {
        decoded = PyString_FromStringAndSize(NULL, PyString_GET_SIZE(raw_data) - num_chars);
    }
    if (!decoded) {
        return NULL;
    }
    str_raw = get_string(raw_data, &string_data);
    str_dec = get_string(decoded, &string_data);

    while (num_chars--) {
        char *next = str_raw;
        while (next < string_data.raw_end) {
            if (*next == ENCODING_PREFIX && 
                *(next+string_data.char_length) >= ENCODING_SHIFT &&
                *(next+string_data.char_length) <= END_ENCODED_CHAR) {
                break;
            }
            next += string_data.char_length;
        }

        if (next > str_raw) {
            Py_MEMCPY(str_dec, str_raw, next - str_raw);
            str_dec += next - str_raw;
        }

        if (string_data.char_length > 1) {
            int i;
            for (i = 0; i < string_data.char_length; i++) {
                str_dec[i] = 0;
            }
        }
        str_dec[0] = (*(next+string_data.char_length)) ^ ENCODING_SHIFT;
        str_dec += string_data.char_length;

        str_raw = next + 2*string_data.char_length;
    }

    copy_ending(raw_data, str_dec, str_raw, &string_data);

    return decoded;
}


static PyMethodDef module_methods[] = {
    {"encode", encode, METH_O, "Encodes the string according to the HS protocol"},
    {"decode", decode, METH_O, "Decodes the string according to the HS protocol"},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC init_speedups(void) {
    (void)Py_InitModule("_speedups", module_methods);
}
